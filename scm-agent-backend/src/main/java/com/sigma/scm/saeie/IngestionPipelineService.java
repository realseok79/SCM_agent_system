package com.sigma.scm.saeie;

import com.opencsv.CSVReader;
import com.sigma.scm.domain.*;
import com.sigma.scm.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class IngestionPipelineService {

    private final ImportBatchRepository importBatchRepository;
    private final BatchStatusHistoryRepository batchStatusHistoryRepository;
    private final StagingInventoryImportRepository stagingInventoryImportRepository;
    private final ExcelParseLogRepository excelParseLogRepository;
    private final RegionInventoryRepository regionInventoryRepository;
    private final RegionRepository regionRepository;
    private final DailyDemandStatsRepository dailyDemandStatsRepository;

    private final HeaderDetector headerDetector;
    private final SemanticMapper semanticMapper;
    private final DriftEngine driftEngine;
    private final RowValidator rowValidator;
    private final SnapshotSerializer snapshotSerializer;

    @Transactional
    public int transitionBatchStatus(
            String batchId,
            BatchStatus nextStatus,
            int currentVersion,
            BatchStatus expectedStatus,
            String changedBy,
            String reason) {

        ImportBatch batch = importBatchRepository.findById(batchId)
                .orElseThrow(() -> new SaeieException.ConflictException("Batch " + batchId + " not found."));

        if (batch.getVersion() != currentVersion) {
            throw new SaeieException.ConflictException(
                    "Version mismatch. Expected: " + currentVersion + ", DB: " + batch.getVersion());
        }

        if (!batch.getStatus().equals(expectedStatus.name())) {
            throw new SaeieException.ConflictException(
                    "Status mismatch. Expected: " + expectedStatus.name() + ", DB: " + batch.getStatus());
        }

        BatchStatus.validateTransition(expectedStatus, nextStatus);

        int nextVersion = batch.getVersion() + 1;
        batch.setStatus(nextStatus.name());
        batch.setVersion(nextVersion);

        LocalDateTime now = LocalDateTime.now();
        if (nextStatus == BatchStatus.PARSED)
            batch.setParsedAt(now);
        if (nextStatus == BatchStatus.APPROVED || nextStatus == BatchStatus.REVIEW_REQUIRED)
            batch.setReviewedAt(now);
        if (nextStatus == BatchStatus.COMMITTED)
            batch.setCommittedAt(now);
        if (nextStatus == BatchStatus.FAILED)
            batch.setFailedAt(now);
        batch.setUpdatedAt(now);

        importBatchRepository.save(batch);

        BatchStatusHistory history = new BatchStatusHistory();
        history.setBatchId(batchId);
        history.setFromStatus(expectedStatus.name());
        history.setToStatus(nextStatus.name());
        history.setChangedBy(changedBy);
        history.setReason(reason);
        batchStatusHistoryRepository.save(history);

        return nextVersion;
    }

    public Map<String, Object> ingestSpreadsheet(
            String companyId,
            MultipartFile file,
            String changedBy) throws Exception {

        long fileSize = file.getSize();
        if (fileSize > 52428800) { // 50MB
            throw new SaeieException.FileTooLargeException("File size exceeds maximum limit of 50MB.");
        }

        byte[] fileBytes = file.getBytes();
        String fileHash = calculateSha256(fileBytes);
        String batchId = "BATCH_" + fileHash.substring(0, 16).toUpperCase() + "_" + System.currentTimeMillis() / 1000;

        // 1. CREATED 배치 레코드 초기 생성
        ImportBatch batch = new ImportBatch();
        batch.setBatchId(batchId);
        batch.setCompanyId(companyId);
        batch.setFileName(file.getOriginalFilename());
        batch.setFileSha256(fileHash);
        batch.setStatus("CREATED");
        batch.setVersion(1);
        batch.setCreatedAt(LocalDateTime.now());
        batch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(batch);

        BatchStatusHistory history = new BatchStatusHistory();
        history.setBatchId(batchId);
        history.setFromStatus(null);
        history.setToStatus("CREATED");
        history.setChangedBy(changedBy);
        history.setReason("Batch ingestion initiated.");
        batchStatusHistoryRepository.save(history);

        int version = 1;

        // 2. 엑셀/CSV 스트림 파싱
        List<List<String>> rows = new ArrayList<>();
        List<String> originalColumns = new ArrayList<>();
        String ext = getFileExtension(file.getOriginalFilename());

        try (InputStream is = file.getInputStream()) {
            if (".csv".equalsIgnoreCase(ext)) {
                parseCsv(is, originalColumns, rows);
            } else if (".xlsx".equalsIgnoreCase(ext) || ".xls".equalsIgnoreCase(ext)) {
                parseExcel(is, originalColumns, rows);
            } else {
                throw new IllegalArgumentException("Unsupported file format: " + ext);
            }
        } catch (Exception e) {
            log.error("[PIPELINE] Failed to read file for batch {}: {}", batchId, e.getMessage(), e);
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.CREATED, changedBy,
                    "Failed to read file: " + e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            res.put("error", "Failed to read file: " + e.getMessage());
            return res;
        }

        // 3. 헤더 탐색 및 정제
        log.info("[PIPELINE] Parsed {} data rows with {} original columns: {}", rows.size(), originalColumns.size(),
                originalColumns);
        int headerIdx = headerDetector.detectHeaderRow(rows, originalColumns, 15);
        log.info("[PIPELINE] Header detection result: headerIdx={}", headerIdx);
        List<String> cleanColumns = new ArrayList<>();
        List<List<String>> cleanRows = new ArrayList<>();

        if (headerIdx == -1) {
            cleanColumns = originalColumns;
            cleanRows = rows;
        } else {
            List<String> headerRow = rows.get(headerIdx);
            for (int i = 0; i < headerRow.size(); i++) {
                String col = headerRow.get(i);
                if (col == null || col.trim().isEmpty()) {
                    cleanColumns.add("UNNAMED_COL_" + i);
                } else {
                    cleanColumns.add(col.trim());
                }
            }
            if (headerIdx + 1 < rows.size()) {
                cleanRows = rows.subList(headerIdx + 1, rows.size());
            }
        }
        log.info("[PIPELINE] Clean columns: {}, Clean rows count: {}", cleanColumns, cleanRows.size());

        // 4. 의미론적 컬럼 매핑 해결 및 드리프트 분석
        Map<String, String> mapping = new LinkedHashMap<>();
        List<String> mappedColsList = new ArrayList<>();
        int unknownColsCount = 0;

        for (String rawCol : cleanColumns) {
            if (rawCol.startsWith("UNNAMED_COL_")) {
                unknownColsCount++;
                mappedColsList.add(null);
                mapping.put(rawCol, null);
                continue;
            }

            Map.Entry<String, Double> mappingResult = semanticMapper.resolveSemanticMapping(companyId, rawCol, 0.40);
            if (mappingResult != null) {
                log.info("[PIPELINE] Column '{}' -> '{}' (confidence: {})", rawCol, mappingResult.getKey(),
                        mappingResult.getValue());
                mappedColsList.add(mappingResult.getKey());
                mapping.put(rawCol, mappingResult.getKey());
            } else {
                log.warn("[PIPELINE] Column '{}' could not be mapped to any standard column", rawCol);
                unknownColsCount++;
                mappedColsList.add(null);
                mapping.put(rawCol, null);
            }
        }

        log.info("[PIPELINE] Mapping result: {} | Unknown columns: {}", mapping, unknownColsCount);

        // 5. 드리프트 차단 검사 (non-fatal)
        double driftScore = 0.0; // default fallback score
        try {
            driftScore = driftEngine.validateDrift(mappedColsList, unknownColsCount);
            log.info("[PIPELINE] Drift score: {}", driftScore);
        } catch (SaeieException.HeaderDriftException e) {
            // Log warning and keep default high penalty driftScore
            log.warn("[PIPELINE] Drift validation warning (non-fatal): {}", e.getMessage());
            driftScore = 0.9; // assign a penalising score
        }

        // CREATED -> PARSED로 상태 전이
        version = transitionBatchStatus(
                batchId, BatchStatus.PARSED, version, BatchStatus.CREATED,
                changedBy, "Header mapping complete. DriftScore: " + driftScore);

        // 6. 행 단위 규칙성 검증
        RowValidator.ValidationResult valResult;
        try {
            valResult = rowValidator.validateRows(cleanRows, cleanColumns, mapping, companyId);
        } catch (Exception e) {
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.PARSED, changedBy,
                    "Row validation crashed: " + e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            return res;
        }

        // 품질 점수 계산: 유효 행 개수 / 전체 행 개수
        long validRowsCount = valResult.payloadList.stream()
                .filter(p -> {
                    @SuppressWarnings("unchecked")
                    List<Map<String, String>> errs = (List<Map<String, String>>) p.get("validation_errors");
                    return errs.stream()
                            .noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
                })
                .count();
        double qualityScore = (double) validRowsCount / Math.max(valResult.payloadList.size(), 1);

        // 직렬화 및 스냅샷 보존
        byte[] snapshotBlob = snapshotSerializer.serializeSnapshot(valResult.payloadList);
        String snapshotChecksum = calculateSha256(snapshotBlob);

        // 점수 및 데이터 스냅샷 업데이트
        ImportBatch updatedBatch = importBatchRepository.findById(batchId).orElseThrow();
        updatedBatch.setDriftScore(driftScore);
        updatedBatch.setQualityScore(qualityScore);
        updatedBatch.setValidatedPayloadSnapshot(snapshotBlob);
        updatedBatch.setSnapshotChecksum(snapshotChecksum);
        updatedBatch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(updatedBatch);

        // 7. 스테이징(Staging) 저장 및 파싱 로그 인입
        for (Map<String, Object> p : valResult.payloadList) {
            @SuppressWarnings("unchecked")
            Map<String, Object> stdVals = (Map<String, Object>) p.get("standardized_values");
            @SuppressWarnings("unchecked")
            List<Map<String, String>> rowErrs = (List<Map<String, String>>) p.get("validation_errors");
            int rowIdx = (Integer) p.get("source_row_index");

            boolean isRowValid = rowErrs.stream()
                    .noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
            String valStatus = isRowValid ? "VALID" : "INVALID";

            StagingInventoryImport staging = new StagingInventoryImport();
            staging.setImportBatchId(batchId);
            staging.setCompanyId(companyId);
            staging.setRegionCode((String) stdVals.get("region_code"));
            staging.setProductName((String) stdVals.get("product_name"));
            staging.setDate((String) stdVals.get("date"));
            staging.setQuantity((Double) stdVals.get("quantity"));
            staging.setValidationStatus(valStatus);
            staging.setSourceRowIndex(rowIdx);
            stagingInventoryImportRepository.save(staging);

            for (Map<String, String> err : rowErrs) {
                ExcelParseLog logEntry = new ExcelParseLog();
                logEntry.setImportBatchId(batchId);
                logEntry.setCompanyId(companyId);
                logEntry.setSeverity(err.get("severity"));
                logEntry.setMessage(err.get("message"));
                logEntry.setColumnName(err.get("column"));
                logEntry.setRowIndex(rowIdx);
                excelParseLogRepository.save(logEntry);
            }
        }

        // 8. 자동 승인 바이패스(Bypass) 검증 및 최종 상태 전이
        Map<String, Object> response = new HashMap<>();
        response.put("batchId", batchId);
        response.put("driftScore", driftScore);
        response.put("qualityScore", qualityScore);
        response.put("mapping", mapping);

        if (driftScore < 0.2 && !valResult.hasCritical && !valResult.hasError) {
            String reasonText = "Bypass automatic approval: perfect schema alignment with zero hard validation errors.";
            if (valResult.hasWarning) {
                long warningCount = valResult.payloadList.stream()
                        .flatMap(p -> {
                            @SuppressWarnings("unchecked")
                            List<Map<String, String>> errs = (List<Map<String, String>>) p.get("validation_errors");
                            return errs.stream();
                        })
                        .filter(e -> "WARNING".equals(e.get("severity")))
                        .count();
                reasonText = "{\"auto_approved_warnings\": true, \"warning_count\": " + warningCount + "}";
            }

            version = transitionBatchStatus(
                    batchId, BatchStatus.APPROVED, version, BatchStatus.PARSED,
                    changedBy, reasonText);

            // Auto-Commit logic: copy from Staging to RegionInventory
            List<StagingInventoryImport> stagingList = stagingInventoryImportRepository.findByImportBatchId(batchId);
            Set<String> processedRegions = new LinkedHashSet<>();
            Set<String> newlyRegisteredRegions = new LinkedHashSet<>();

            for (StagingInventoryImport staging : stagingList) {
                if ("VALID".equals(staging.getValidationStatus())) {
                    String rCode = staging.getRegionCode();
                    processedRegions.add(rCode);

                    // 1. 방어 로직: DB에 지역 코드가 없다면 자동 생성 (FK 에러 방지)
                    if (regionRepository.findByRegionCode(rCode).isEmpty()) {
                        com.sigma.scm.domain.Region newRegion = new com.sigma.scm.domain.Region();
                        newRegion.setRegionCode(rCode);
                        newRegion.setRegionName(rCode); // 이름이 없으므로 코드로 대체
                        newRegion.setDescription("Auto-registered via Excel Upload");
                        regionRepository.save(newRegion);
                        newlyRegisteredRegions.add(rCode);
                        log.info("[PIPELINE] Auto-registered missing region: {}", rCode);
                    }

                    // 2. 재고 반입 커밋
                    RegionInventory inv = new RegionInventory();
                    inv.setId(new RegionInventoryId(rCode, staging.getProductName(), staging.getDate()));
                    inv.setQuantity(staging.getQuantity());
                    inv.setSourceBatchId(batchId);
                    regionInventoryRepository.save(inv);

                    // 3. 일일 수요 통계 기본값 생성 (무결성 검증 통과용)
                    DailyDemandStatsId statsId = new DailyDemandStatsId(rCode, staging.getProductName(),
                            staging.getDate());
                    if (dailyDemandStatsRepository.findById(statsId).isEmpty()) {
                        DailyDemandStats stats = new DailyDemandStats();
                        stats.setId(statsId);
                        stats.setDailyOutboundTotal(0.0);
                        stats.setMovingAvg30d(0.0);
                        dailyDemandStatsRepository.save(stats);
                    }
                }
            }
            transitionBatchStatus(
                    batchId, BatchStatus.COMMITTED, version, BatchStatus.APPROVED,
                    "SYSTEM", "Idempotent auto-commit: Auto-committed APPROVED batch");

            response.put("status", BatchStatus.COMMITTED.name());
            response.put("processedRegions", new ArrayList<>(processedRegions));
            response.put("newlyRegisteredRegions", new ArrayList<>(newlyRegisteredRegions));
        } else if (valResult.hasCritical) {
            transitionBatchStatus(
                    batchId, BatchStatus.FAILED, version, BatchStatus.PARSED,
                    changedBy, "Automatic ingestion aborted: critical validation errors detected.");
            response.put("status", BatchStatus.FAILED.name());
        } else {
            transitionBatchStatus(
                    batchId, BatchStatus.REVIEW_REQUIRED, version, BatchStatus.PARSED,
                    changedBy,
                    "Batch diverted to Review: DriftScore (" + driftScore + ") or validation warnings/errors present.");
            response.put("status", BatchStatus.REVIEW_REQUIRED.name());
        }

        return response;
    }

    @Transactional
    public Map<String, Object> confirmSpreadsheet(String batchId, Map<String, String> userOverrides, String changedBy) {
        ImportBatch batch = importBatchRepository.findById(batchId)
                .orElseThrow(() -> new SaeieException.ConflictException("Batch " + batchId + " not found."));

        BatchStatus currentStatus = BatchStatus.valueOf(batch.getStatus());
        int version = batch.getVersion();

        // REVIEW_REQUIRED 라면 APPROVED 로 수동 전환을 먼저 수행한 뒤 COMMITTED 로 전이
        if (currentStatus == BatchStatus.REVIEW_REQUIRED) {
            version = transitionBatchStatus(
                batchId, BatchStatus.APPROVED, version, BatchStatus.REVIEW_REQUIRED,
                changedBy, "Manually approved and overrides validated."
            );
        }

        // APPROVED -> COMMITTED 상태 전이
        transitionBatchStatus(
            batchId, BatchStatus.COMMITTED, version, BatchStatus.APPROVED,
            changedBy, "Batch integrated to RegionInventory."
        );

        // StagingInventoryImport에서 VALID 상태의 임시 데이터들을 RegionInventory 실재고 테이블로 적재 (UPSERT)
        List<StagingInventoryImport> stgList = stagingInventoryImportRepository.findByImportBatchId(batchId);
        int committedCount = 0;

        for (StagingInventoryImport stg : stgList) {
            if ("VALID".equals(stg.getValidationStatus())) {
                RegionInventoryId invId = new RegionInventoryId(stg.getRegionCode(), stg.getProductName(), stg.getDate());
                RegionInventory inv = regionInventoryRepository.findByIdForUpdate(invId).orElse(new RegionInventory());
                inv.setId(invId);
                inv.setQuantity(stg.getQuantity());
                inv.setSourceBatchId(batchId);
                inv.setUpdatedAt(LocalDateTime.now());
                regionInventoryRepository.save(inv);
                committedCount++;
            }
        }

        Map<String, Object> res = new HashMap<>();
        res.put("batchId", batchId);
        res.put("status", BatchStatus.COMMITTED.name());
        res.put("committedCount", committedCount);
        return res;
    }

    public Map<String, Object> analyzeSpreadsheet(String companyId, MultipartFile file) throws Exception {
        long fileSize = file.getSize();
        if (fileSize > 52428800) { // 50MB
            throw new SaeieException.FileTooLargeException("File size exceeds maximum limit of 50MB.");
        }

        List<List<String>> rows = new ArrayList<>();
        List<String> originalColumns = new ArrayList<>();
        String ext = getFileExtension(file.getOriginalFilename());

        try (InputStream is = file.getInputStream()) {
            if (".csv".equalsIgnoreCase(ext)) {
                parseCsv(is, originalColumns, rows);
            } else if (".xlsx".equalsIgnoreCase(ext) || ".xls".equalsIgnoreCase(ext)) {
                parseExcel(is, originalColumns, rows);
            } else {
                throw new IllegalArgumentException("Unsupported file format: " + ext);
            }
        }

        // 3. 헤더 탐색 및 정제
        int headerIdx = headerDetector.detectHeaderRow(rows, originalColumns, 15);
        List<String> cleanColumns = new ArrayList<>();
        List<List<String>> cleanRows = new ArrayList<>();

        if (headerIdx == -1) {
            cleanColumns = originalColumns;
            cleanRows = rows;
        } else {
            List<String> headerRow = rows.get(headerIdx);
            for (int i = 0; i < headerRow.size(); i++) {
                String col = headerRow.get(i);
                if (col == null || col.trim().isEmpty()) {
                    cleanColumns.add("UNNAMED_COL_" + i);
                } else {
                    cleanColumns.add(col.trim());
                }
            }
            if (headerIdx + 1 < rows.size()) {
                cleanRows = rows.subList(headerIdx + 1, rows.size());
            }
        }

        // 4. 의미론적 컬럼 매핑 해결 및 드리프트 분석
        Map<String, String> mapping = new LinkedHashMap<>();
        List<String> mappedColsList = new ArrayList<>();
        int unknownColsCount = 0;

        for (String rawCol : cleanColumns) {
            if (rawCol.startsWith("UNNAMED_COL_")) {
                unknownColsCount++;
                mappedColsList.add(null);
                mapping.put(rawCol, null);
                continue;
            }

            Map.Entry<String, Double> mappingResult = semanticMapper.resolveSemanticMapping(companyId, rawCol, 0.40);
            if (mappingResult != null) {
                mappedColsList.add(mappingResult.getKey());
                mapping.put(rawCol, mappingResult.getKey());
            } else {
                unknownColsCount++;
                mappedColsList.add(null);
                mapping.put(rawCol, null);
            }
        }

        // 5. 드리프트 차단 검사
        double driftScore = driftEngine.validateDrift(mappedColsList, unknownColsCount);

        // 6. 행 단위 규칙성 검증
        RowValidator.ValidationResult valResult = rowValidator.validateRows(cleanRows, cleanColumns, mapping, companyId);

        // 품질 점수 계산
        long validRowsCount = valResult.payloadList.stream()
                .filter(p -> {
                    @SuppressWarnings("unchecked")
                    List<Map<String, String>> errs = (List<Map<String, String>>) p.get("validation_errors");
                    return errs.stream()
                            .noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
                })
                .count();
        double qualityScore = (double) validRowsCount / Math.max(valResult.payloadList.size(), 1);

        Map<String, Object> response = new HashMap<>();
        response.put("driftScore", driftScore);
        response.put("qualityScore", qualityScore);
        response.put("mapping", mapping);
        response.put("columns", cleanColumns);
        response.put("previewRows", cleanRows.subList(0, Math.min(cleanRows.size(), 10)));
        response.put("validationResult", valResult.payloadList);
        response.put("status", "SUCCESS");
        return response;
    }

    @Transactional
    public Map<String, Object> confirmSpreadsheet(
            String companyId,
            MultipartFile file,
            String changedBy,
            Map<String, String> userMapping) throws Exception {

        long fileSize = file.getSize();
        if (fileSize > 52428800) { // 50MB
            throw new SaeieException.FileTooLargeException("File size exceeds maximum limit of 50MB.");
        }

        byte[] fileBytes = file.getBytes();
        String fileHash = calculateSha256(fileBytes);
        String batchId = "BATCH_" + fileHash.substring(0, 16).toUpperCase() + "_" + System.currentTimeMillis() / 1000;

        ImportBatch batch = new ImportBatch();
        batch.setBatchId(batchId);
        batch.setCompanyId(companyId);
        batch.setFileName(file.getOriginalFilename());
        batch.setFileSha256(fileHash);
        batch.setStatus("CREATED");
        batch.setVersion(1);
        batch.setCreatedAt(LocalDateTime.now());
        batch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(batch);

        BatchStatusHistory history = new BatchStatusHistory();
        history.setBatchId(batchId);
        history.setFromStatus(null);
        history.setToStatus("CREATED");
        history.setChangedBy(changedBy);
        history.setReason("Batch confirmation initiated.");
        batchStatusHistoryRepository.save(history);

        int version = 1;

        List<List<String>> rows = new ArrayList<>();
        List<String> originalColumns = new ArrayList<>();
        String ext = getFileExtension(file.getOriginalFilename());

        try (InputStream is = file.getInputStream()) {
            if (".csv".equalsIgnoreCase(ext)) {
                parseCsv(is, originalColumns, rows);
            } else if (".xlsx".equalsIgnoreCase(ext) || ".xls".equalsIgnoreCase(ext)) {
                parseExcel(is, originalColumns, rows);
            } else {
                throw new IllegalArgumentException("Unsupported file format: " + ext);
            }
        } catch (Exception e) {
            log.error("[PIPELINE] Failed to read file for batch {}: {}", batchId, e.getMessage(), e);
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.CREATED, changedBy,
                    "Failed to read file: " + e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            res.put("error", "Failed to read file: " + e.getMessage());
            return res;
        }

        int headerIdx = headerDetector.detectHeaderRow(rows, originalColumns, 15);
        List<String> cleanColumns = new ArrayList<>();
        List<List<String>> cleanRows = new ArrayList<>();

        if (headerIdx == -1) {
            cleanColumns = originalColumns;
            cleanRows = rows;
        } else {
            List<String> headerRow = rows.get(headerIdx);
            for (int i = 0; i < headerRow.size(); i++) {
                String col = headerRow.get(i);
                if (col == null || col.trim().isEmpty()) {
                    cleanColumns.add("UNNAMED_COL_" + i);
                } else {
                    cleanColumns.add(col.trim());
                }
            }
            if (headerIdx + 1 < rows.size()) {
                cleanRows = rows.subList(headerIdx + 1, rows.size());
            }
        }

        List<String> mappedColsList = new ArrayList<>();
        int unknownColsCount = 0;

        for (String rawCol : cleanColumns) {
            String mapped = userMapping.get(rawCol);
            mappedColsList.add(mapped);
            if (mapped == null) {
                unknownColsCount++;
            }
        }

        double driftScore;
        try {
            driftScore = driftEngine.validateDrift(mappedColsList, unknownColsCount);
        } catch (SaeieException.HeaderDriftException e) {
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.CREATED, changedBy, e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            res.put("error", e.getMessage());
            return res;
        }

        version = transitionBatchStatus(
                batchId, BatchStatus.PARSED, version, BatchStatus.CREATED,
                changedBy, "Header mapping confirmed by user. DriftScore: " + driftScore);

        RowValidator.ValidationResult valResult;
        try {
            valResult = rowValidator.validateRows(cleanRows, cleanColumns, userMapping, companyId);
        } catch (Exception e) {
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.PARSED, changedBy,
                    "Row validation crashed: " + e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            return res;
        }

        long validRowsCount = valResult.payloadList.stream()
                .filter(p -> {
                    @SuppressWarnings("unchecked")
                    List<Map<String, String>> errs = (List<Map<String, String>>) p.get("validation_errors");
                    return errs.stream()
                            .noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
                })
                .count();
        double qualityScore = (double) validRowsCount / Math.max(valResult.payloadList.size(), 1);

        byte[] snapshotBlob = snapshotSerializer.serializeSnapshot(valResult.payloadList);
        String snapshotChecksum = calculateSha256(snapshotBlob);

        ImportBatch updatedBatch = importBatchRepository.findById(batchId).orElseThrow();
        updatedBatch.setDriftScore(driftScore);
        updatedBatch.setQualityScore(qualityScore);
        updatedBatch.setValidatedPayloadSnapshot(snapshotBlob);
        updatedBatch.setSnapshotChecksum(snapshotChecksum);
        updatedBatch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(updatedBatch);

        for (Map<String, Object> p : valResult.payloadList) {
            @SuppressWarnings("unchecked")
            Map<String, Object> stdVals = (Map<String, Object>) p.get("standardized_values");
            @SuppressWarnings("unchecked")
            List<Map<String, String>> rowErrs = (List<Map<String, String>>) p.get("validation_errors");
            int rowIdx = (Integer) p.get("source_row_index");

            boolean isRowValid = rowErrs.stream()
                    .noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
            String valStatus = isRowValid ? "VALID" : "INVALID";

            StagingInventoryImport staging = new StagingInventoryImport();
            staging.setImportBatchId(batchId);
            staging.setCompanyId(companyId);
            staging.setRegionCode((String) stdVals.get("region_code"));
            staging.setProductName((String) stdVals.get("product_name"));
            staging.setDate((String) stdVals.get("date"));
            staging.setQuantity((Double) stdVals.get("quantity"));
            staging.setValidationStatus(valStatus);
            staging.setSourceRowIndex(rowIdx);
            stagingInventoryImportRepository.save(staging);

            for (Map<String, String> err : rowErrs) {
                ExcelParseLog logEntry = new ExcelParseLog();
                logEntry.setImportBatchId(batchId);
                logEntry.setCompanyId(companyId);
                logEntry.setSeverity(err.get("severity"));
                logEntry.setMessage(err.get("message"));
                logEntry.setColumnName(err.get("column"));
                logEntry.setRowIndex(rowIdx);
                excelParseLogRepository.save(logEntry);
            }
        }

        Map<String, Object> response = new HashMap<>();
        response.put("batchId", batchId);
        response.put("driftScore", driftScore);
        response.put("qualityScore", qualityScore);
        response.put("mapping", userMapping);

        if (driftScore < 0.2 && !valResult.hasCritical && !valResult.hasError) {
            String reasonText = "User approved and schema aligned. Auto-committed.";
            version = transitionBatchStatus(
                    batchId, BatchStatus.APPROVED, version, BatchStatus.PARSED,
                    changedBy, reasonText);

            List<StagingInventoryImport> stagingList = stagingInventoryImportRepository.findByImportBatchId(batchId);
            Set<String> processedRegions = new LinkedHashSet<>();
            Set<String> newlyRegisteredRegions = new LinkedHashSet<>();

            for (StagingInventoryImport staging : stagingList) {
                if ("VALID".equals(staging.getValidationStatus())) {
                    String rCode = staging.getRegionCode();
                    processedRegions.add(rCode);

                    if (regionRepository.findByRegionCode(rCode).isEmpty()) {
                        com.sigma.scm.domain.Region newRegion = new com.sigma.scm.domain.Region();
                        newRegion.setRegionCode(rCode);
                        newRegion.setRegionName(rCode);
                        newRegion.setDescription("Auto-registered via Excel Upload");
                        regionRepository.save(newRegion);
                        newlyRegisteredRegions.add(rCode);
                        log.info("[PIPELINE] Auto-registered missing region: {}", rCode);
                    }

                    RegionInventoryId invId = new RegionInventoryId(rCode, staging.getProductName(), staging.getDate());
                    RegionInventory inv = regionInventoryRepository.findByIdForUpdate(invId).orElse(new RegionInventory());
                    inv.setId(invId);
                    inv.setQuantity(staging.getQuantity());
                    inv.setSourceBatchId(batchId);
                    inv.setUpdatedAt(LocalDateTime.now());
                    regionInventoryRepository.save(inv);

                    DailyDemandStatsId statsId = new DailyDemandStatsId(rCode, staging.getProductName(),
                            staging.getDate());
                    if (dailyDemandStatsRepository.findById(statsId).isEmpty()) {
                        DailyDemandStats stats = new DailyDemandStats();
                        stats.setId(statsId);
                        stats.setDailyOutboundTotal(0.0);
                        stats.setMovingAvg30d(0.0);
                        dailyDemandStatsRepository.save(stats);
                    }
                }
            }
            transitionBatchStatus(
                    batchId, BatchStatus.COMMITTED, version, BatchStatus.APPROVED,
                    "SYSTEM", "Idempotent auto-commit: Auto-committed APPROVED batch");

            response.put("status", BatchStatus.COMMITTED.name());
            response.put("processedRegions", new ArrayList<>(processedRegions));
            response.put("newlyRegisteredRegions", new ArrayList<>(newlyRegisteredRegions));
        } else if (valResult.hasCritical) {
            transitionBatchStatus(
                    batchId, BatchStatus.FAILED, version, BatchStatus.PARSED,
                    changedBy, "Automatic ingestion aborted: critical validation errors detected.");
            response.put("status", BatchStatus.FAILED.name());
        } else {
            transitionBatchStatus(
                    batchId, BatchStatus.REVIEW_REQUIRED, version, BatchStatus.PARSED,
                    changedBy,
                    "Batch diverted to Review: DriftScore (" + driftScore + ") or validation warnings/errors present.");
            response.put("status", BatchStatus.REVIEW_REQUIRED.name());
        }

        return response;
    }

    private void parseCsv(InputStream is, List<String> originalColumns, List<List<String>> rows) throws Exception {
        try (CSVReader reader = new CSVReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String[] line;
            boolean firstLine = true;
            while ((line = reader.readNext()) != null) {
                if (firstLine) {
                    originalColumns.addAll(Arrays.asList(line));
                    firstLine = false;
                } else {
                    rows.add(Arrays.asList(line));
                }
            }
        }
    }

    // ── Inner class: parsed result from one Excel sheet ──
    private static class SheetParseResult {
        String sheetName;
        int sheetIdx;
        List<String> headers = new ArrayList<>();       // cleaned header names
        List<List<String>> dataRows = new ArrayList<>(); // data rows below header
        int headerRowIdx;                               // which physical row was the header
        Set<String> matchedStdCols = new HashSet<>();    // which of the 4 required SCM cols this sheet covers
        int score;                                       // relevance score
    }

    /**
     * Scans ALL sheets in the workbook, finds the header row dynamically (up to 15 rows deep),
     * and either picks the single best sheet OR merges data from multiple sheets when the
     * required SCM columns (region_code, product_name, date, quantity) are spread across sheets.
     */
    private void parseExcel(InputStream is, List<String> originalColumns, List<List<String>> rows) throws Exception {
        try (Workbook workbook = WorkbookFactory.create(is)) {
            int sheetCount = workbook.getNumberOfSheets();
            log.info("[PIPELINE] Workbook has {} sheet(s)", sheetCount);

            Set<String> requiredStdCols = Set.of("region_code", "product_name", "date", "quantity");
            int MAX_HEADER_SCAN = 15; // scan up to this many rows for the header

            // ──────── PHASE 1: Analyze every sheet ────────
            List<SheetParseResult> sheetResults = new ArrayList<>();

            for (int s = 0; s < sheetCount; s++) {
                Sheet sheet = workbook.getSheetAt(s);
                if (sheet.getPhysicalNumberOfRows() == 0) continue;

                // Find the best header row within the first MAX_HEADER_SCAN rows
                int bestHeaderRow = -1;
                int bestHeaderScore = -1;
                Set<String> bestMatchedCols = new HashSet<>();
                List<String> bestHeaderValues = new ArrayList<>();

                int lastRowToScan = Math.min(sheet.getLastRowNum(), sheet.getFirstRowNum() + MAX_HEADER_SCAN - 1);
                for (int r = sheet.getFirstRowNum(); r <= lastRowToScan; r++) {
                    Row row = sheet.getRow(r);
                    if (row == null) continue;

                    int rowScore = 0;
                    Set<String> rowMatchedCols = new HashSet<>();
                    List<String> rowHeaderVals = new ArrayList<>();
                    boolean hasAnyText = false;

                    for (int c = 0; c < row.getLastCellNum(); c++) {
                        Cell cell = row.getCell(c, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                        String rawVal = getCellValueAsString(cell);
                        String val = HeaderDetector.cleanValue(rawVal);
                        rowHeaderVals.add(rawVal != null ? rawVal.trim() : "");

                        if (val.isEmpty()) continue;
                        hasAnyText = true;

                        for (Map.Entry<String, List<String>> entry : HeaderDetector.COLUMN_ALIASES.entrySet()) {
                            if (entry.getValue().contains(val)) {
                                if (requiredStdCols.contains(entry.getKey())) {
                                    rowScore += 10;
                                } else {
                                    rowScore += 1;
                                }
                                rowMatchedCols.add(entry.getKey());
                                break;
                            }
                        }
                    }

                    // Bonus: if this row looks like pure text labels (no numeric-only cells) it's more likely a header
                    if (hasAnyText && rowScore > bestHeaderScore) {
                        bestHeaderScore = rowScore;
                        bestHeaderRow = r;
                        bestMatchedCols = rowMatchedCols;
                        bestHeaderValues = rowHeaderVals;
                    }
                }

                if (bestHeaderRow < 0) continue; // no usable header found

                // Read data rows below the detected header
                SheetParseResult spr = new SheetParseResult();
                spr.sheetName = sheet.getSheetName();
                spr.sheetIdx = s;
                spr.headerRowIdx = bestHeaderRow;
                spr.headers.addAll(bestHeaderValues);
                spr.matchedStdCols.addAll(bestMatchedCols);
                spr.score = bestHeaderScore;

                for (int r = bestHeaderRow + 1; r <= sheet.getLastRowNum(); r++) {
                    Row row = sheet.getRow(r);
                    if (row == null) continue;
                    List<String> rowList = new ArrayList<>();
                    int maxCol = Math.max(row.getLastCellNum(), spr.headers.size());
                    for (int c = 0; c < maxCol; c++) {
                        Cell cell = row.getCell(c, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                        rowList.add(getCellValueAsString(cell));
                    }
                    // Skip completely empty rows
                    boolean allEmpty = rowList.stream().allMatch(v -> v == null || v.trim().isEmpty());
                    if (!allEmpty) {
                        spr.dataRows.add(rowList);
                    }
                }

                log.info("[PIPELINE] Sheet '{}' (idx={}) header at row {}, score={}, matched SCM cols={}, data rows={}",
                        spr.sheetName, spr.sheetIdx, spr.headerRowIdx, spr.score,
                        spr.matchedStdCols, spr.dataRows.size());

                if (!spr.dataRows.isEmpty()) {
                    sheetResults.add(spr);
                }
            }

            if (sheetResults.isEmpty()) {
                log.warn("[PIPELINE] No sheet with valid data found. Falling back to first sheet raw parse.");
                Sheet fallback = workbook.getSheetAt(0);
                Iterator<Row> ri = fallback.rowIterator();
                boolean first = true;
                while (ri.hasNext()) {
                    Row row = ri.next();
                    List<String> rl = new ArrayList<>();
                    for (int c = 0; c < row.getLastCellNum(); c++) {
                        rl.add(getCellValueAsString(row.getCell(c, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK)));
                    }
                    if (first) { originalColumns.addAll(rl); first = false; } else { rows.add(rl); }
                }
                return;
            }

            // ──────── PHASE 2: Decide strategy ────────
            // Sort sheets by score descending
            sheetResults.sort((a, b) -> Integer.compare(b.score, a.score));

            // Check if the best sheet alone covers all 4 required columns
            SheetParseResult best = sheetResults.get(0);
            Set<String> bestCoverage = new HashSet<>(best.matchedStdCols);
            bestCoverage.retainAll(requiredStdCols);

            if (bestCoverage.size() >= 4 || sheetResults.size() == 1) {
                // ── STRATEGY A: Single sheet has everything (or it's the only sheet) ──
                log.info("[PIPELINE] Using single sheet strategy: '{}' covers {} of 4 required cols",
                        best.sheetName, bestCoverage.size());
                originalColumns.addAll(best.headers);
                rows.addAll(best.dataRows);
            } else {
                // ── STRATEGY B: Merge multiple sheets ──
                log.info("[PIPELINE] Single sheet '{}' only covers {}. Attempting multi-sheet merge.",
                        best.sheetName, bestCoverage);

                // Greedily pick sheets that together cover all required cols
                List<SheetParseResult> selectedSheets = new ArrayList<>();
                Set<String> coveredSoFar = new HashSet<>();

                for (SheetParseResult spr : sheetResults) {
                    Set<String> newCols = new HashSet<>(spr.matchedStdCols);
                    newCols.retainAll(requiredStdCols);
                    newCols.removeAll(coveredSoFar);
                    if (!newCols.isEmpty() || selectedSheets.isEmpty()) {
                        selectedSheets.add(spr);
                        coveredSoFar.addAll(spr.matchedStdCols);
                    }
                    if (coveredSoFar.containsAll(requiredStdCols)) break;
                }

                log.info("[PIPELINE] Selected {} sheets for merge: {}", selectedSheets.size(),
                        selectedSheets.stream().map(sp -> sp.sheetName + "(cols=" + sp.matchedStdCols + ")").toList());

                if (selectedSheets.size() == 1) {
                    // Only one sheet contributes – just use it
                    SheetParseResult single = selectedSheets.get(0);
                    originalColumns.addAll(single.headers);
                    rows.addAll(single.dataRows);
                } else {
                    // ── Merge strategy: combine columns from all selected sheets ──
                    // Build unified header
                    List<String> mergedHeaders = new ArrayList<>();
                    Map<SheetParseResult, Integer> sheetOffsetMap = new LinkedHashMap<>();

                    for (SheetParseResult sp : selectedSheets) {
                        sheetOffsetMap.put(sp, mergedHeaders.size());
                        for (int i = 0; i < sp.headers.size(); i++) {
                            String h = sp.headers.get(i);
                            // Avoid duplicate header names by prefixing with sheet name
                            if (mergedHeaders.contains(h)) {
                                mergedHeaders.add(sp.sheetName + "_" + h);
                            } else {
                                mergedHeaders.add(h);
                            }
                        }
                    }
                    originalColumns.addAll(mergedHeaders);

                    // Find the sheet with the most data rows to use as the "primary" driving sheet
                    SheetParseResult primarySheet = selectedSheets.stream()
                            .max(Comparator.comparingInt(sp -> sp.dataRows.size()))
                            .orElse(selectedSheets.get(0));

                    // Build lookup tables for secondary sheets (keyed by likely join columns)
                    // We try to join on any matching column value between sheets
                    for (int rowIdx = 0; rowIdx < primarySheet.dataRows.size(); rowIdx++) {
                        List<String> mergedRow = new ArrayList<>(Collections.nCopies(mergedHeaders.size(), ""));

                        // Fill primary sheet's columns
                        int pOffset = sheetOffsetMap.get(primarySheet);
                        List<String> pRow = primarySheet.dataRows.get(rowIdx);
                        for (int c = 0; c < pRow.size() && (pOffset + c) < mergedRow.size(); c++) {
                            mergedRow.set(pOffset + c, pRow.get(c));
                        }

                        // For each secondary sheet, try to find the best matching row
                        for (SheetParseResult secSheet : selectedSheets) {
                            if (secSheet == primarySheet) continue;
                            int sOffset = sheetOffsetMap.get(secSheet);

                            // Try to find a matching row in the secondary sheet
                            // Strategy: look for any shared cell value between the primary row
                            // and the secondary sheet's rows (fuzzy cross-reference)
                            List<String> bestSecRow = null;
                            int bestMatchCount = 0;

                            Set<String> primaryValues = new HashSet<>();
                            for (String v : pRow) {
                                if (v != null && !v.trim().isEmpty()) primaryValues.add(v.trim().toLowerCase());
                            }

                            for (List<String> secRow : secSheet.dataRows) {
                                int matchCount = 0;
                                for (String sv : secRow) {
                                    if (sv != null && !sv.trim().isEmpty() && primaryValues.contains(sv.trim().toLowerCase())) {
                                        matchCount++;
                                    }
                                }
                                if (matchCount > bestMatchCount) {
                                    bestMatchCount = matchCount;
                                    bestSecRow = secRow;
                                }
                            }

                            if (bestSecRow != null && bestMatchCount > 0) {
                                for (int c = 0; c < bestSecRow.size() && (sOffset + c) < mergedRow.size(); c++) {
                                    mergedRow.set(sOffset + c, bestSecRow.get(c));
                                }
                            } else if (rowIdx < secSheet.dataRows.size()) {
                                // Fallback: positional merge (same row index)
                                List<String> secRow = secSheet.dataRows.get(rowIdx);
                                for (int c = 0; c < secRow.size() && (sOffset + c) < mergedRow.size(); c++) {
                                    mergedRow.set(sOffset + c, secRow.get(c));
                                }
                            }
                        }

                        rows.add(mergedRow);
                    }

                    log.info("[PIPELINE] Multi-sheet merge complete. Merged headers: {}, Merged rows: {}",
                            mergedHeaders.size(), rows.size());
                }
            }
        }
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null)
            return "";
        return switch (cell.getCellType()) {
            case STRING -> cell.getStringCellValue();
            case NUMERIC -> {
                if (DateUtil.isCellDateFormatted(cell)) {
                    yield cell.getLocalDateTimeCellValue().toString();
                } else {
                    double d = cell.getNumericCellValue();
                    if (d == (long) d) {
                        yield String.valueOf((long) d);
                    } else {
                        yield String.valueOf(d);
                    }
                }
            }
            case BOOLEAN -> String.valueOf(cell.getBooleanCellValue());
            case FORMULA -> {
                try {
                    yield cell.getStringCellValue();
                } catch (Exception e) {
                    yield String.valueOf(cell.getNumericCellValue());
                }
            }
            default -> "";
        };
    }

    private String calculateSha256(byte[] bytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(bytes);
        StringBuilder hexString = new StringBuilder();
        for (byte b : hash) {
            String hex = Integer.toHexString(0xff & b);
            if (hex.length() == 1)
                hexString.append('0');
            hexString.append(hex);
        }
        return hexString.toString();
    }

    private String getFileExtension(String filename) {
        if (filename == null || !filename.contains("."))
            return "";
        return filename.substring(filename.lastIndexOf("."));
    }
}
