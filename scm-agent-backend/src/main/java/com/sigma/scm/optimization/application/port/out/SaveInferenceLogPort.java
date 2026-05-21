package com.sigma.scm.optimization.application.port.out;

import com.sigma.scm.optimization.domain.model.ReorderDecision;

public interface SaveInferenceLogPort {
    void saveInferenceLog(ReorderDecision decision);
}
