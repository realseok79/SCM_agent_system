package com.sigma.scm.optimization.domain.model;

import lombok.Builder;
import lombok.Value;

@Value
@Builder
public class OptimizationItem {
    String productName;
    String abcClass;
    double unitPrice;
    double holdingCostRate;
    double orderingCostFixed;
    int baseLeadTimeDays;
    double minOrderQty;
    double lotSize;
}
