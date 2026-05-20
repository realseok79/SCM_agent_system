package com.sigma.scm.saeie;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

public class BatchStateMachineTest {

    @Test
    public void testValidStateTransitions() {
        // CREATED -> PARSED
        assertDoesNotThrow(() -> BatchStatus.validateTransition(BatchStatus.CREATED, BatchStatus.PARSED));

        // PARSED -> APPROVED
        assertDoesNotThrow(() -> BatchStatus.validateTransition(BatchStatus.PARSED, BatchStatus.APPROVED));

        // APPROVED -> COMMITTED
        assertDoesNotThrow(() -> BatchStatus.validateTransition(BatchStatus.APPROVED, BatchStatus.COMMITTED));
    }

    @Test
    public void testInvalidStateTransitions() {
        // CREATED -> COMMITTED (Cannot skip parsing/approval)
        assertThrows(IllegalArgumentException.class, () -> {
            BatchStatus.validateTransition(BatchStatus.CREATED, BatchStatus.COMMITTED);
        });

        // COMMITTED -> FAILED (Final status cannot transition to failure)
        assertThrows(IllegalArgumentException.class, () -> {
            BatchStatus.validateTransition(BatchStatus.COMMITTED, BatchStatus.FAILED);
        });
    }

    @Test
    public void testRevokingStateTransitions() {
        // APPROVED -> REVOKING (Rollback initiated)
        assertDoesNotThrow(() -> BatchStatus.validateTransition(BatchStatus.APPROVED, BatchStatus.REVOKING));

        // REVOKING -> REVIEW_REQUIRED (Rollback execution complete)
        assertDoesNotThrow(() -> BatchStatus.validateTransition(BatchStatus.REVOKING, BatchStatus.REVIEW_REQUIRED));
    }
}
