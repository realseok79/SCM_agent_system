package com.sigma.scm.optimization.domain.service.filter;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Component
@Order(1) // 1단계: MOQ 필터
public class MoqFilter implements ConstraintFilter {
    @Override
    public double apply(OptimizationItem item, double inputQty) {
        if (inputQty <= 0) return 0.0;
        return Math.max(inputQty, item.getMinOrderQty());
    }
}
