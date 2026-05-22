package com.sigma.scm.saeie;

import com.sigma.scm.domain.*;
import com.sigma.scm.repository.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.mock.web.MockMultipartFile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class IngestionPipelineServiceTest {

    @Mock
    private ImportBatchRepository importBatchRepository;
    @Mock
    private BatchStatusHistoryRepository batchStatusHistoryRepository;
    @Mock
    private StagingInventoryImportRepository stagingInventoryImportRepository;
    @Mock
    private ExcelParseLogRepository excelParseLogRepository;
    @Mock
    private RegionInventoryRepository regionInventoryRepository;
    @Mock
    private RegionRepository regionRepository;
    @Mock
    private DailyDemandStatsRepository dailyDemandStatsRepository;

    @Mock
    private HeaderDetector headerDetector;
    @Mock
    private SemanticMapper semanticMapper;
    @Mock
    private DriftEngine driftEngine;
    @Mock
    private RowValidator rowValidator;
    @Mock
    private SnapshotSerializer snapshotSerializer;

    @InjectMocks
    private IngestionPipelineService ingestionPipelineService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testIngestSpreadsheetSuccess() throws Exception {
        String companyId = "SIGMA";
        String changedBy = "admin";
        
        // Mock data
        String csvContent = "region_code,product_name,date,quantity\nKR-11,Mask,2026-05-20,150.0\n";
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.csv", "text/csv", csvContent.getBytes()
        );

        ImportBatch batch = new ImportBatch();
        batch.setBatchId("BATCH_TEST");
        batch.setVersion(1);
        batch.setStatus("CREATED");
        when(importBatchRepository.findById(anyString())).thenReturn(Optional.of(batch));

        // Mock HeaderDetector
        when(headerDetector.detectHeaderRow(any(), any(), anyInt())).thenReturn(0);

        // Mock SemanticMapper
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("region_code"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("region_code", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("product_name"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("product_name", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("date"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("date", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("quantity"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("quantity", 1.0));

        // Mock DriftEngine
        when(driftEngine.validateDrift(any(), anyInt())).thenReturn(0.0);

        // Mock RowValidator
        RowValidator.ValidationResult valResult = new RowValidator.ValidationResult();
        valResult.hasCritical = false;
        valResult.hasError = false;
        valResult.hasWarning = false;
        valResult.payloadList = new ArrayList<>();
        
        Map<String, Object> payloadRow = new HashMap<>();
        payloadRow.put("source_row_index", 1);
        
        Map<String, Object> stdVals = new HashMap<>();
        stdVals.put("region_code", "KR-11");
        stdVals.put("product_name", "Mask");
        stdVals.put("date", "2026-05-20");
        stdVals.put("quantity", 150.0);
        payloadRow.put("standardized_values", stdVals);
        payloadRow.put("validation_errors", new ArrayList<Map<String, String>>());
        valResult.payloadList.add(payloadRow);
        
        when(rowValidator.validateRows(any(), any(), any(), anyString())).thenReturn(valResult);

        // Mock SnapshotSerializer
        when(snapshotSerializer.serializeSnapshot(any())).thenReturn(new byte[]{1, 2, 3});

        // Mock Staging list for post-approval commit
        StagingInventoryImport staging = new StagingInventoryImport();
        staging.setValidationStatus("VALID");
        staging.setRegionCode("KR-11");
        staging.setProductName("Mask");
        staging.setDate("2026-05-20");
        staging.setQuantity(150.0);
        when(stagingInventoryImportRepository.findByImportBatchId(anyString()))
                .thenReturn(Collections.singletonList(staging));

        // Mock region checking
        when(regionRepository.findByRegionCode("KR-11")).thenReturn(Optional.of(new com.sigma.scm.domain.Region()));

        // Run ingestion
        Map<String, Object> response = ingestionPipelineService.ingestSpreadsheet(companyId, file, changedBy);

        // Assertions
        assertNotNull(response);
        assertEquals("COMMITTED", response.get("status"));
        assertTrue(((List<?>) response.get("processedRegions")).contains("KR-11"));

        // Verify status changes
        verify(importBatchRepository, atLeastOnce()).save(any(ImportBatch.class));
        verify(stagingInventoryImportRepository, times(1)).save(any(StagingInventoryImport.class));
        verify(regionInventoryRepository, times(1)).save(any(RegionInventory.class));
        verify(dailyDemandStatsRepository, times(1)).save(any(DailyDemandStats.class));
    }

    @Test
    public void testIngestMultiSheetExcelSuccess() throws Exception {
        String companyId = "SIGMA";
        String changedBy = "admin";

        // Create a multi-sheet Excel file programmatically
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (org.apache.poi.xssf.usermodel.XSSFWorkbook workbook = new org.apache.poi.xssf.usermodel.XSSFWorkbook()) {
            // Sheet 1: Region & Product Info
            org.apache.poi.ss.usermodel.Sheet sheet1 = workbook.createSheet("Region_Product");
            org.apache.poi.ss.usermodel.Row header1 = sheet1.createRow(0);
            header1.createCell(0).setCellValue("region_code");
            header1.createCell(1).setCellValue("product_name");
            org.apache.poi.ss.usermodel.Row row1 = sheet1.createRow(1);
            row1.createCell(0).setCellValue("KR-11");
            row1.createCell(1).setCellValue("Mask");

            // Sheet 2: Date & Quantity Info
            org.apache.poi.ss.usermodel.Sheet sheet2 = workbook.createSheet("Date_Qty");
            org.apache.poi.ss.usermodel.Row header2 = sheet2.createRow(0);
            header2.createCell(0).setCellValue("date");
            header2.createCell(1).setCellValue("quantity");
            org.apache.poi.ss.usermodel.Row row2 = sheet2.createRow(1);
            row2.createCell(0).setCellValue("2026-05-20");
            row2.createCell(1).setCellValue("150.0");

            workbook.write(bos);
        }

        MockMultipartFile file = new MockMultipartFile(
                "file", "test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", bos.toByteArray()
        );

        ImportBatch batch = new ImportBatch();
        batch.setBatchId("BATCH_TEST_MULTI");
        batch.setVersion(1);
        batch.setStatus("CREATED");
        when(importBatchRepository.findById(anyString())).thenReturn(Optional.of(batch));

        // Mock HeaderDetector
        when(headerDetector.detectHeaderRow(any(), any(), anyInt())).thenReturn(0);

        // Mock SemanticMapper
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("region_code"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("region_code", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("product_name"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("product_name", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("date"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("date", 1.0));
        when(semanticMapper.resolveSemanticMapping(eq(companyId), eq("quantity"), anyDouble()))
                .thenReturn(new AbstractMap.SimpleEntry<>("quantity", 1.0));

        // Mock DriftEngine
        when(driftEngine.validateDrift(any(), anyInt())).thenReturn(0.0);

        // Mock RowValidator
        RowValidator.ValidationResult valResult = new RowValidator.ValidationResult();
        valResult.hasCritical = false;
        valResult.hasError = false;
        valResult.hasWarning = false;
        valResult.payloadList = new ArrayList<>();

        Map<String, Object> payloadRow = new HashMap<>();
        payloadRow.put("source_row_index", 1);

        Map<String, Object> stdVals = new HashMap<>();
        stdVals.put("region_code", "KR-11");
        stdVals.put("product_name", "Mask");
        stdVals.put("date", "2026-05-20");
        stdVals.put("quantity", 150.0);
        payloadRow.put("standardized_values", stdVals);
        payloadRow.put("validation_errors", new ArrayList<Map<String, String>>());
        valResult.payloadList.add(payloadRow);

        when(rowValidator.validateRows(any(), any(), any(), anyString())).thenReturn(valResult);

        // Mock SnapshotSerializer
        when(snapshotSerializer.serializeSnapshot(any())).thenReturn(new byte[]{1, 2, 3});

        // Mock Staging list for post-approval commit
        StagingInventoryImport staging = new StagingInventoryImport();
        staging.setValidationStatus("VALID");
        staging.setRegionCode("KR-11");
        staging.setProductName("Mask");
        staging.setDate("2026-05-20");
        staging.setQuantity(150.0);
        when(stagingInventoryImportRepository.findByImportBatchId(anyString()))
                .thenReturn(Collections.singletonList(staging));

        // Mock region checking
        when(regionRepository.findByRegionCode("KR-11")).thenReturn(Optional.of(new com.sigma.scm.domain.Region()));

        // Run ingestion
        Map<String, Object> response = ingestionPipelineService.ingestSpreadsheet(companyId, file, changedBy);

        // Assertions
        assertNotNull(response);
        assertEquals("COMMITTED", response.get("status"));
        assertTrue(((List<?>) response.get("processedRegions")).contains("KR-11"));
    }
}

