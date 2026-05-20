package com.sigma.scm.saeie;

import java.util.EnumSet;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public enum BatchStatus {
    CREATED,
    PARSED,
    APPROVED,
    REVIEW_REQUIRED,
    COMMITTED,
    REVOKING,
    FAILED,
    ROLLED_BACK;

    private static final Map<BatchStatus, Set<BatchStatus>> ALLOWED_TRANSITIONS = new HashMap<>();

    static {
        ALLOWED_TRANSITIONS.put(CREATED, EnumSet.of(PARSED, FAILED));
        ALLOWED_TRANSITIONS.put(PARSED, EnumSet.of(APPROVED, REVIEW_REQUIRED, FAILED));
        ALLOWED_TRANSITIONS.put(REVIEW_REQUIRED, EnumSet.of(APPROVED, FAILED, ROLLED_BACK));
        ALLOWED_TRANSITIONS.put(APPROVED, EnumSet.of(COMMITTED, REVOKING));
        ALLOWED_TRANSITIONS.put(REVOKING, EnumSet.of(REVIEW_REQUIRED, FAILED));
        ALLOWED_TRANSITIONS.put(COMMITTED, EnumSet.noneOf(BatchStatus.class));
        ALLOWED_TRANSITIONS.put(FAILED, EnumSet.noneOf(BatchStatus.class));
        ALLOWED_TRANSITIONS.put(ROLLED_BACK, EnumSet.noneOf(BatchStatus.class));
    }

    public static void validateTransition(BatchStatus from, BatchStatus to) {
        if (from == COMMITTED || from == FAILED || from == ROLLED_BACK) {
            throw new IllegalArgumentException("Terminal state '" + from + "' is immutable.");
        }
        Set<BatchStatus> allowed = ALLOWED_TRANSITIONS.get(from);
        if (allowed == null || !allowed.contains(to)) {
            throw new IllegalArgumentException("Invalid transition path from '" + from + "' to '" + to + "'.");
        }
    }
}
