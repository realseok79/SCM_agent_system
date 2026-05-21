package com.sigma.scm.optimization.domain.service.filter;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

@Component
@Order(2) // 2단계: Lot Size 필터
public class LotSizeFilter implements ConstraintFilter {
    @Override
    public double apply(OptimizationItem item, double inputQty) {
        if (inputQty <= 0) return 0.0;
        double lotSize = item.getLotSize();
        if (lotSize <= 0) return inputQty;
        return Math.ceil(inputQty / lotSize) * lotSize;
    }
}
