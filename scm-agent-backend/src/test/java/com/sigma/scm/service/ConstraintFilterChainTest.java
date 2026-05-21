package com.sigma.scm.service;

import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.optimization.domain.service.filter.ConstraintFilter;
import com.sigma.scm.optimization.domain.service.filter.ConstraintFilterChain;
import com.sigma.scm.optimization.domain.service.filter.LotSizeFilter;
import com.sigma.scm.optimization.domain.service.filter.MoqFilter;
import org.junit.jupiter.api.Test;
import java.util.Arrays;
import static org.junit.jupiter.api.Assertions.*;

public class ConstraintFilterChainTest {

    @Test
    public void testFiltersAndChain() {
        OptimizationItem item = OptimizationItem.builder()
                .productName("Test_Item")
                .minOrderQty(100.0)
                .lotSize(50.0)
                .build();

        ConstraintFilter moqFilter = new MoqFilter();
        ConstraintFilter lotSizeFilter = new LotSizeFilter();

        // MOQ filter test: 30.0 -> max(30, 100) -> 100.0
        assertEquals(100.0, moqFilter.apply(item, 30.0));
        // MOQ filter test: 120.0 -> max(120, 100) -> 120.0
        assertEquals(120.0, moqFilter.apply(item, 120.0));

        // LotSize filter test: 100.0 -> ceil(100/50)*50 -> 100.0
        assertEquals(100.0, lotSizeFilter.apply(item, 100.0));
        // LotSize filter test: 120.0 -> ceil(120/50)*50 -> 150.0
        assertEquals(150.0, lotSizeFilter.apply(item, 120.0));

        // Chain processing: initialQty 30.0 -> MOQ(100.0) -> LotSize(100.0)
        ConstraintFilterChain chain = new ConstraintFilterChain(Arrays.asList(moqFilter, lotSizeFilter));
        assertEquals(100.0, chain.process(item, 30.0));

        // Chain processing: initialQty 101.0 -> MOQ(101.0) -> LotSize(150.0)
        assertEquals(150.0, chain.process(item, 101.0));
    }

    @Test
    public void testBoundaryValueAnalysis() {
        ConstraintFilter moqFilter = new MoqFilter();
        ConstraintFilter lotSizeFilter = new LotSizeFilter();
        ConstraintFilterChain chain = new ConstraintFilterChain(Arrays.asList(moqFilter, lotSizeFilter));

        // 1. Exact boundaries: MOQ = 100.0, LotSize = 50.0
        OptimizationItem standardItem = OptimizationItem.builder()
                .productName("Standard")
                .minOrderQty(100.0)
                .lotSize(50.0)
                .build();

        // Inputs around MOQ boundary (100.0)
        assertEquals(100.0, chain.process(standardItem, 99.9));
        assertEquals(100.0, chain.process(standardItem, 100.0));
        assertEquals(150.0, chain.process(standardItem, 100.1));

        // Inputs around next Lot boundary (150.0)
        assertEquals(150.0, chain.process(standardItem, 149.9));
        assertEquals(150.0, chain.process(standardItem, 150.0));
        assertEquals(200.0, chain.process(standardItem, 150.1));

        // 2. Zero & negative inputs
        assertEquals(0.0, chain.process(standardItem, 0.0));
        assertEquals(0.0, chain.process(standardItem, -50.0));

        // 3. No constraints (Zero limits)
        OptimizationItem freeItem = OptimizationItem.builder()
                .productName("Free")
                .minOrderQty(0.0)
                .lotSize(0.0)
                .build();

        assertEquals(0.0, chain.process(freeItem, 0.0));
        assertEquals(42.42, chain.process(freeItem, 42.42), 0.001);
        assertEquals(1000.0, chain.process(freeItem, 1000.0), 0.001);

        // 4. Negative constraint values protection
        OptimizationItem negativeConstrainedItem = OptimizationItem.builder()
                .productName("Negative")
                .minOrderQty(-10.0)
                .lotSize(-5.0)
                .build();

        assertEquals(10.0, chain.process(negativeConstrainedItem, 10.0));
        assertEquals(0.0, chain.process(negativeConstrainedItem, -5.0));
    }

    @Test
    public void testStepFunctionLotSizeBoundaries() {
        ConstraintFilter moqFilter = new MoqFilter();
        ConstraintFilter lotSizeFilter = new LotSizeFilter();
        ConstraintFilterChain chain = new ConstraintFilterChain(Arrays.asList(moqFilter, lotSizeFilter));

        // Lot Size = 500.0, MOQ = 0.0
        OptimizationItem largeLotItem = OptimizationItem.builder()
                .productName("LargeLotItem")
                .minOrderQty(0.0)
                .lotSize(500.0)
                .build();

        // 1. 499.0일 때 올림 연산으로 500.0이 되는지 검증 (좌극한 부근)
        assertEquals(500.0, chain.process(largeLotItem, 499.0));

        // 2. 정확히 500.0일 때 500.0이 되는지 검증 (경계값)
        assertEquals(500.0, chain.process(largeLotItem, 500.0));

        // 3. 500.1일 때 올림 연산으로 1000.0이 되는지 검증 (우극한 부근)
        assertEquals(1000.0, chain.process(largeLotItem, 500.1));
        
        // 4. 0.1일 때 올림 연산으로 500.0이 되는지 검증
        assertEquals(500.0, chain.process(largeLotItem, 0.1));
    }
}
