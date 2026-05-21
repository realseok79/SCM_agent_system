package com.sigma.scm.optimization.domain.service.filter;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ConstraintFilterChain {
    
    // Spring이 @Order에 따라 오름차순으로 자동 주입함
    private final List<ConstraintFilter> filters;

    public double process(OptimizationItem item, double initialQty) {
        double currentQty = initialQty;
        for (ConstraintFilter filter : filters) {
            currentQty = filter.apply(item, currentQty);
        }
        return currentQty;
    }
}
