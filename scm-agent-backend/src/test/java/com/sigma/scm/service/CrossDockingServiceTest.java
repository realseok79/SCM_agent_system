package com.sigma.scm.service;

import com.sigma.scm.domain.InventoryRebalancingOrder;
import com.sigma.scm.domain.ProductFinancialMaster;
import com.sigma.scm.repository.InventoryRebalancingOrderRepository;
import com.sigma.scm.repository.ProductFinancialMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class CrossDockingServiceTest {

    @Mock
    private RegionInventoryRepository regionInventoryRepository;

    @Mock
    private ProductFinancialMasterRepository productFinancialMasterRepository;

    @Mock
    private InventoryRebalancingOrderRepository rebalancingOrderRepository;

    @InjectMocks
    private CrossDockingService crossDockingService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testCrossDockingRebalancing() {
        String productName = "Mask";
        String maxDate = "2026-05-19";

        when(regionInventoryRepository.findMaxDate()).thenReturn(maxDate);

        List<Object[]> candidates = new ArrayList<>();
        candidates.add(new Object[]{"US", 1000.0, 10.0});
        when(regionInventoryRepository.findCrossDockingCandidates(productName, maxDate)).thenReturn(candidates);

        ProductFinancialMaster fin = new ProductFinancialMaster();
        fin.setProductName(productName);
        fin.setUnitPrice(500);
        when(productFinancialMasterRepository.findById(productName)).thenReturn(Optional.of(fin));

        CrossDockingService.RebalanceResult result = crossDockingService.attemptCrossDocking(productName, 50.0);

        assertEquals(50.0, result.getRebalancedQty());
        assertEquals(0.0, result.getRemainingPoQty());
        assertEquals(1, result.getTransfers().size());

        InventoryRebalancingOrder order = result.getTransfers().get(0);
        assertEquals("US", order.getFromRegion());
        assertEquals("GLOBAL_ORDER", order.getToRegion());
        assertEquals(50, order.getTransferQty());
        assertEquals(25000, order.getSavedCost());
        assertEquals("APPROVED", order.getStatus());

        verify(rebalancingOrderRepository, times(1)).save(any(InventoryRebalancingOrder.class));
    }

    @Test
    public void testCrossDockingNoCandidates() {
        String productName = "Mask";
        String maxDate = "2026-05-19";

        when(regionInventoryRepository.findMaxDate()).thenReturn(maxDate);
        when(regionInventoryRepository.findCrossDockingCandidates(productName, maxDate)).thenReturn(new ArrayList<>());

        CrossDockingService.RebalanceResult result = crossDockingService.attemptCrossDocking(productName, 50.0);

        assertEquals(0.0, result.getRebalancedQty());
        assertEquals(50.0, result.getRemainingPoQty());
        assertTrue(result.getTransfers().isEmpty());
    }

    @Test
    public void testCrossDockingSurplusLimit() {
        String productName = "Mask";
        String maxDate = "2026-05-19";

        when(regionInventoryRepository.findMaxDate()).thenReturn(maxDate);

        // quantity=1000.0, movingAvg30d=10.0 -> DoS=100 days. Surplus above 90 days = 1000 - 900 = 100.
        List<Object[]> candidates = new ArrayList<>();
        candidates.add(new Object[]{"US", 1000.0, 10.0});
        when(regionInventoryRepository.findCrossDockingCandidates(productName, maxDate)).thenReturn(candidates);

        ProductFinancialMaster fin = new ProductFinancialMaster();
        fin.setProductName(productName);
        fin.setUnitPrice(500);
        when(productFinancialMasterRepository.findById(productName)).thenReturn(Optional.of(fin));

        // Request 150, but surplus is only 100
        CrossDockingService.RebalanceResult result = crossDockingService.attemptCrossDocking(productName, 150.0);

        assertEquals(100.0, result.getRebalancedQty());
        assertEquals(50.0, result.getRemainingPoQty());
        assertEquals(1, result.getTransfers().size());
        assertEquals(100, result.getTransfers().get(0).getTransferQty());
    }
}
