package com.sigma.scm.service;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.optimization.domain.model.ReorderDecision;
import com.sigma.scm.optimization.domain.service.OptimizationEngine;
import org.junit.jupiter.api.Test;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

public class OptimizationEngineTest {

    private final OptimizationEngine engine = new OptimizationEngine();

    @Test
    public void testCalculateEOQ() {
        OptimizationItem item = OptimizationItem.builder()
                .productName("SemiConductor_A")
                .abcClass("A")
                .unitPrice(100.00)
                .holdingCostRate(0.20)
                .orderingCostFixed(10.00)
                .baseLeadTimeDays(3)
                .build();

        double eoq = engine.calculateEOQ(item, 10.0);
        assertEquals(60.415, eoq, 0.01);
    }

    @Test
    public void testColdStartDecision() {
        OptimizationItem item = OptimizationItem.builder()
                .productName("SemiConductor_A")
                .abcClass("A")
                .unitPrice(100.00)
                .holdingCostRate(0.20)
                .orderingCostFixed(10.00)
                .baseLeadTimeDays(3)
                .build();

        ReorderDecision decision = engine.makeDecision(
                item,
                "KR-SL",
                10.0,
                10.0,
                30,
                0.0, 0.0, 0.0,
                Collections.emptyMap(),
                "none"
        );

        assertTrue(decision.isColdStart());
        assertTrue(decision.isTriggerReorder());
        assertEquals(38.49, decision.getRop(), 0.01);
    }

    @Test
    public void testAIModeDecision() {
        OptimizationItem item = OptimizationItem.builder()
                .productName("SemiConductor_A")
                .abcClass("A")
                .unitPrice(100.00)
                .holdingCostRate(0.20)
                .orderingCostFixed(10.00)
                .baseLeadTimeDays(3)
                .build();

        Map<String, Double> shap = new HashMap<>();
        shap.put("lag_1", 0.42);

        ReorderDecision decision = engine.makeDecision(
                item,
                "KR-SL",
                10.0,
                100.0,
                100,
                11.0, 15.0, 25.0,
                shap,
                "global_base_v1.0"
        );

        assertFalse(decision.isColdStart());
        assertFalse(decision.isTriggerReorder());
        assertEquals(75.0, decision.getRop(), 0.01);
        assertEquals(30.0, decision.getSafetyStock(), 0.01);
        assertEquals("global_base_v1.0", decision.getModelVersion());
        assertEquals(0.42, decision.getShapValues().get("lag_1"));
    }

    @Test
    public void testBoundaryValuesAndExceptionSafety() {
        // 1. calculateEOQ null safety
        assertEquals(0.0, engine.calculateEOQ(null, 10.0));

        // 2. Division by zero in holding cost protection
        OptimizationItem freeHoldingItem = OptimizationItem.builder()
                .productName("FreeHolding")
                .unitPrice(0.0) // Cause division by zero
                .holdingCostRate(0.0)
                .orderingCostFixed(10.0)
                .build();
        double eoqZeroH = engine.calculateEOQ(freeHoldingItem, 10.0);
        // Annual demand = 3650.0, s = 10.0. H = 1.0 (fallback).
        // EOQ = sqrt(2 * 3650 * 10 / 1.0) = sqrt(73000) = 270.185
        assertEquals(270.185, eoqZeroH, 0.01);

        // 3. Negatives check
        OptimizationItem negativeItem = OptimizationItem.builder()
                .productName("Negative")
                .unitPrice(-100.0)
                .holdingCostRate(-0.2)
                .orderingCostFixed(-10.0)
                .baseLeadTimeDays(-5) // Negative lead time
                .build();
        // Negatives should be coerced to 0 or positive
        assertEquals(0.0, engine.calculateEOQ(negativeItem, -10.0));

        // 4. makeDecision null item validation
        assertThrows(IllegalArgumentException.class, () -> 
            engine.makeDecision(null, "KR", 10, 10, 10, 0, 0, 0, null, null)
        );

        // 5. Mixed-case and null ABC classes
        OptimizationItem mixedAbcItem = OptimizationItem.builder()
                .productName("MixedAbc")
                .abcClass("  a ") // mixed case with space
                .baseLeadTimeDays(4)
                .build();
        ReorderDecision decA = engine.makeDecision(mixedAbcItem, "KR", 10.0, 10.0, 30, 0, 0, 0, null, null);
        assertTrue(decA.isColdStart());
        // Z-score for A = 1.96. sigma = 2.5. safetyStock = 1.96 * 2.5 * sqrt(4) = 9.8.
        assertEquals(9.8, decA.getSafetyStock(), 0.01);

        // 6. NaN/Infinity propagation defensive check
        OptimizationItem nanItem = OptimizationItem.builder()
                .productName("NanItem")
                .abcClass(null) // null class
                .build();
        ReorderDecision decNan = engine.makeDecision(
                nanItem,
                null,
                Double.NaN,
                Double.NEGATIVE_INFINITY,
                100, // AI Mode
                Double.NaN,
                Double.NaN,
                Double.NaN,
                null,
                null
        );
        assertEquals(0.0, decNan.getSafetyStock());
        assertEquals(0.0, decNan.getRop());
        assertEquals(0.0, decNan.getEoq());
        assertEquals("unknown", decNan.getRegionCode());
        assertEquals("none", decNan.getModelVersion());
        assertTrue(decNan.isTriggerReorder()); // currentStock = -Inf, rop = 0.0 -> true
    }
}
