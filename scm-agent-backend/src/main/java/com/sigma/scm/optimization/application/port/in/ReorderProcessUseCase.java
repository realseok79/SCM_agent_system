package com.sigma.scm.optimization.application.port.in;

import com.sigma.scm.optimization.domain.model.ReorderDecision;

public interface ReorderProcessUseCase {
    ReorderDecision evaluateReorder(String productName, String regionCode);
}
