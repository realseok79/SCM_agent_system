package com.sigma.scm.saeie;

import com.sigma.scm.domain.ImportBatch;
import com.sigma.scm.repository.BatchStatusHistoryRepository;
import com.sigma.scm.repository.ImportBatchRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class RollbackEngineTest {

    private ImportBatchRepository importBatchRepository;
    private RegionInventoryRepository regionInventoryRepository;
    private BatchStatusHistoryRepository batchStatusHistoryRepository;
    private RollbackEngine rollbackEngine;

    @BeforeEach
    public void setUp() {
        importBatchRepository = mock(ImportBatchRepository.class);
        regionInventoryRepository = mock(RegionInventoryRepository.class);
        batchStatusHistoryRepository = mock(BatchStatusHistoryRepository.class);
        
        rollbackEngine = new RollbackEngine(
                importBatchRepository,
                regionInventoryRepository,
                batchStatusHistoryRepository
        );
    }

    @Test
    public void testSuccessfulRollbackWorkflow() {
        String batchId = "BATCH_TEST_123";
        ImportBatch batch = new ImportBatch();
        batch.setBatchId(batchId);
        batch.setStatus("APPROVED");
        batch.setVersion(1);

        when(importBatchRepository.findById(batchId)).thenReturn(Optional.of(batch));

        int finalVersion = rollbackEngine.rollbackBatch(batchId, 1, "TEST_USER");

        assertEquals(3, finalVersion); // 1 -> 2 (REVOKING) -> 3 (REVIEW_REQUIRED)
        assertEquals("REVIEW_REQUIRED", batch.getStatus());
        
        verify(regionInventoryRepository, times(1)).deleteBySourceBatchId(batchId);
        verify(importBatchRepository, times(2)).save(batch);
        verify(batchStatusHistoryRepository, times(2)).save(any());
    }

    @Test
    public void testVersionMismatchThrowsConflictException() {
        String batchId = "BATCH_TEST_123";
        ImportBatch batch = new ImportBatch();
        batch.setBatchId(batchId);
        batch.setStatus("APPROVED");
        batch.setVersion(2); // DB version is 2

        when(importBatchRepository.findById(batchId)).thenReturn(Optional.of(batch));

        // Expect exception when trying to rollback with version 1
        assertThrows(SaeieException.ConflictException.class, () -> {
            rollbackEngine.rollbackBatch(batchId, 1, "TEST_USER");
        });

        verify(regionInventoryRepository, never()).deleteBySourceBatchId(anyString());
    }
}
