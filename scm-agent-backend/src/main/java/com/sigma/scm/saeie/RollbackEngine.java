package com.sigma.scm.saeie;

import com.sigma.scm.domain.BatchStatusHistory;
import com.sigma.scm.domain.ImportBatch;
import com.sigma.scm.repository.BatchStatusHistoryRepository;
import com.sigma.scm.repository.ImportBatchRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
@Slf4j
public class RollbackEngine {

    private final ImportBatchRepository importBatchRepository;
    private final RegionInventoryRepository regionInventoryRepository;
    private final BatchStatusHistoryRepository batchStatusHistoryRepository;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public int lockBatchForRollback(String batchId, int currentVersion, String changedBy) {
        ImportBatch batch = importBatchRepository.findById(batchId)
                .orElseThrow(() -> new SaeieException.ConflictException("Batch " + batchId + " not found."));

        if (batch.getVersion() != currentVersion) {
            throw new SaeieException.ConflictException("Version mismatch. Expected: " + currentVersion + ", DB: " + batch.getVersion());
        }

        if (!"APPROVED".equals(batch.getStatus())) {
            throw new SaeieException.ConflictException("Cannot rollback batch " + batchId + ": status must be APPROVED, got '" + batch.getStatus() + "'.");
        }

        BatchStatus.validateTransition(BatchStatus.valueOf(batch.getStatus()), BatchStatus.REVOKING);

        int nextVersion = batch.getVersion() + 1;
        batch.setStatus("REVOKING");
        batch.setVersion(nextVersion);
        batch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(batch);

        BatchStatusHistory history = new BatchStatusHistory();
        history.setBatchId(batchId);
        history.setFromStatus("APPROVED");
        history.setToStatus("REVOKING");
        history.setChangedBy(changedBy);
        history.setReason("Rollback initiated: batch status locked to REVOKING.");
        batchStatusHistoryRepository.save(history);

        return nextVersion;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public int executePhysicalRollback(String batchId, int currentVersion, String changedBy) {
        ImportBatch batch = importBatchRepository.findById(batchId)
                .orElseThrow(() -> new SaeieException.ConflictException("Batch " + batchId + " not found."));

        if (batch.getVersion() != currentVersion) {
            throw new SaeieException.ConflictException("Version mismatch. Expected: " + currentVersion + ", DB: " + batch.getVersion());
        }

        // Delete all inventory records introduced by this batch
        regionInventoryRepository.deleteBySourceBatchId(batchId);

        BatchStatus.validateTransition(BatchStatus.REVOKING, BatchStatus.REVIEW_REQUIRED);

        int finalVersion = batch.getVersion() + 1;
        batch.setStatus("REVIEW_REQUIRED");
        batch.setVersion(finalVersion);
        batch.setUpdatedAt(LocalDateTime.now());
        importBatchRepository.save(batch);

        BatchStatusHistory history = new BatchStatusHistory();
        history.setBatchId(batchId);
        history.setFromStatus("REVOKING");
        history.setToStatus("REVIEW_REQUIRED");
        history.setChangedBy(changedBy);
        history.setReason("Rollback execution complete: physical rows removed.");
        batchStatusHistoryRepository.save(history);

        return finalVersion;
    }

    @Transactional
    public void handleRollbackCrash(String batchId, String changedBy, Exception e) {
        try {
            ImportBatch batch = importBatchRepository.findById(batchId).orElse(null);
            if (batch != null) {
                batch.setStatus("FAILED");
                batch.setUpdatedAt(LocalDateTime.now());
                importBatchRepository.save(batch);

                BatchStatusHistory history = new BatchStatusHistory();
                history.setBatchId(batchId);
                history.setFromStatus("REVOKING");
                history.setToStatus("FAILED");
                history.setChangedBy(changedBy);
                history.setReason("Rollback crashed: " + e.getMessage());
                batchStatusHistoryRepository.save(history);
            }
        } catch (Exception ex) {
            log.error("Failed to transition batch to FAILED during rollback crash handler", ex);
        }
    }

    public int rollbackBatch(String batchId, int currentVersion, String changedBy) {
        int nextVersion;
        try {
            nextVersion = lockBatchForRollback(batchId, currentVersion, changedBy);
        } catch (Exception e) {
            log.error("Rollback locking phase failed for batch: {}", batchId, e);
            throw e;
        }

        try {
            return executePhysicalRollback(batchId, nextVersion, changedBy);
        } catch (Exception e) {
            log.error("Rollback execution phase crashed for batch: {}. Demoting to FAILED.", batchId, e);
            handleRollbackCrash(batchId, changedBy, e);
            throw e;
        }
    }
}
