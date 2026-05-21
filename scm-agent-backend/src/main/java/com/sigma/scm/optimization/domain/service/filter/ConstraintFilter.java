package com.sigma.scm.optimization.domain.service.filter;

import com.sigma.scm.optimization.domain.model.OptimizationItem;

public interface ConstraintFilter {
    double apply(OptimizationItem item, double inputQty);
}
