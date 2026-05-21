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
}
