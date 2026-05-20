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
            throw new SaeieException.ConflictException("Version mismatch. Expected: " + currentVersion + ", DB: " + batch.getVersion());
        }

        if (!batch.getStatus().equals(expectedStatus.name())) {
            throw new SaeieException.ConflictException("Status mismatch. Expected: " + expectedStatus.name() + ", DB: " + batch.getStatus());
        }

        BatchStatus.validateTransition(expectedStatus, nextStatus);

        int nextVersion = batch.getVersion() + 1;
        batch.setStatus(nextStatus.name());
        batch.setVersion(nextVersion);
        
        LocalDateTime now = LocalDateTime.now();
        if (nextStatus == BatchStatus.PARSED) batch.setParsedAt(now);
        if (nextStatus == BatchStatus.APPROVED || nextStatus == BatchStatus.REVIEW_REQUIRED) batch.setReviewedAt(now);
        if (nextStatus == BatchStatus.COMMITTED) batch.setCommittedAt(now);
        if (nextStatus == BatchStatus.FAILED) batch.setFailedAt(now);
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
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.CREATED, changedBy, "Failed to read file: " + e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            res.put("error", "Failed to read file: " + e.getMessage());
            return res;
        }

        // 3. 헤더 탐색 및 정제
        log.info("[PIPELINE] Parsed {} data rows with {} original columns: {}", rows.size(), originalColumns.size(), originalColumns);
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
                log.info("[PIPELINE] Column '{}' -> '{}' (confidence: {})", rawCol, mappingResult.getKey(), mappingResult.getValue());
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

        // 5. 드리프트 차단 검사
        double driftScore;
        try {
            driftScore = driftEngine.validateDrift(mappedColsList, unknownColsCount);
            log.info("[PIPELINE] Drift score: {}", driftScore);
        } catch (SaeieException.HeaderDriftException e) {
            log.error("[PIPELINE] Drift validation failed: {}", e.getMessage());
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.CREATED, changedBy, e.getMessage());
            Map<String, Object> res = new HashMap<>();
            res.put("batchId", batchId);
            res.put("status", BatchStatus.FAILED.name());
            res.put("error", e.getMessage());
            return res;
        }

        // CREATED -> PARSED로 상태 전이
        version = transitionBatchStatus(
            batchId, BatchStatus.PARSED, version, BatchStatus.CREATED,
            changedBy, "Header mapping complete. DriftScore: " + driftScore
        );

        // 6. 행 단위 규칙성 검증
        RowValidator.ValidationResult valResult;
        try {
            valResult = rowValidator.validateRows(cleanRows, cleanColumns, mapping, companyId);
        } catch (Exception e) {
            transitionBatchStatus(batchId, BatchStatus.FAILED, version, BatchStatus.PARSED, changedBy, "Row validation crashed: " + e.getMessage());
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
                    return errs.stream().noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
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

            boolean isRowValid = rowErrs.stream().noneMatch(e -> "CRITICAL".equals(e.get("severity")) || "ERROR".equals(e.get("severity")));
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
                changedBy, reasonText
            );
            
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
                    DailyDemandStatsId statsId = new DailyDemandStatsId(rCode, staging.getProductName(), staging.getDate());
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
                "SYSTEM", "Idempotent auto-commit: Auto-committed APPROVED batch"
            );
            
            response.put("status", BatchStatus.COMMITTED.name());
            response.put("processedRegions", new ArrayList<>(processedRegions));
            response.put("newlyRegisteredRegions", new ArrayList<>(newlyRegisteredRegions));
        } else if (valResult.hasCritical) {
            transitionBatchStatus(
                batchId, BatchStatus.FAILED, version, BatchStatus.PARSED,
                changedBy, "Automatic ingestion aborted: critical validation errors detected."
            );
            response.put("status", BatchStatus.FAILED.name());
        } else {
            transitionBatchStatus(
                batchId, BatchStatus.REVIEW_REQUIRED, version, BatchStatus.PARSED,
                changedBy, "Batch diverted to Review: DriftScore (" + driftScore + ") or validation warnings/errors present."
            );
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

    private void parseExcel(InputStream is, List<String> originalColumns, List<List<String>> rows) throws Exception {
        try (Workbook workbook = WorkbookFactory.create(is)) {
            int sheetCount = workbook.getNumberOfSheets();
            log.info("[PIPELINE] Workbook has {} sheet(s)", sheetCount);

            // Required SCM columns for scoring each sheet
            Set<String> requiredStdCols = Set.of("region_code", "product_name", "date", "quantity");

            int bestSheetIdx = 0;
            int bestScore = -1;

            // Scan all sheets to find the one with the best SCM column match
            for (int s = 0; s < sheetCount; s++) {
                Sheet sheet = workbook.getSheetAt(s);
                if (sheet.getPhysicalNumberOfRows() == 0) continue;

                Row firstRow = sheet.getRow(sheet.getFirstRowNum());
                if (firstRow == null) continue;

                int score = 0;
                for (int i = 0; i < firstRow.getLastCellNum(); i++) {
                    Cell cell = firstRow.getCell(i, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                    String val = HeaderDetector.cleanValue(getCellValueAsString(cell));
                    if (val.isEmpty()) continue;

                    for (Map.Entry<String, List<String>> entry : HeaderDetector.COLUMN_ALIASES.entrySet()) {
                        if (requiredStdCols.contains(entry.getKey()) && entry.getValue().contains(val)) {
                            score += 10; // Required column match = high score
                            break;
                        } else if (entry.getValue().contains(val)) {
                            score += 1; // Optional column match = low score
                            break;
                        }
                    }
                }

                log.info("[PIPELINE] Sheet '{}' (idx={}) column match score: {}", sheet.getSheetName(), s, score);

                if (score > bestScore) {
                    bestScore = score;
                    bestSheetIdx = s;
                }
            }

            Sheet selectedSheet = workbook.getSheetAt(bestSheetIdx);
            log.info("[PIPELINE] Selected sheet '{}' (idx={}) with best score {}", 
                    selectedSheet.getSheetName(), bestSheetIdx, bestScore);

            // Parse the selected sheet
            Iterator<Row> rowIterator = selectedSheet.rowIterator();
            boolean firstLine = true;

            while (rowIterator.hasNext()) {
                Row row = rowIterator.next();
                List<String> rowList = new ArrayList<>();
                
                for (int i = 0; i < row.getLastCellNum(); i++) {
                    Cell cell = row.getCell(i, Row.MissingCellPolicy.CREATE_NULL_AS_BLANK);
                    rowList.add(getCellValueAsString(cell));
                }

                if (firstLine) {
                    originalColumns.addAll(rowList);
                    firstLine = false;
                } else {
                    rows.add(rowList);
                }
            }
        }
    }

    private String getCellValueAsString(Cell cell) {
        if (cell == null) return "";
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
            if (hex.length() == 1) hexString.append('0');
            hexString.append(hex);
        }
        return hexString.toString();
    }

    private String getFileExtension(String filename) {
        if (filename == null || !filename.contains(".")) return "";
        return filename.substring(filename.lastIndexOf("."));
    }
}
