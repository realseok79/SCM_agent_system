package com.sigma.scm.optimization.domain.model;

import lombok.Builder;
import lombok.Value;

import java.util.Map;

@Value
@Builder
public class ReorderDecision {
    String productName;
    String regionCode;
    double eoq;
    double rop;
    double predictedDemand10;
    double predictedDemand50;
    double predictedDemand90;
    double safetyStock;
    boolean isColdStart;
    boolean triggerReorder;
    Map<String, Double> shapValues;
    String modelVersion;
}
