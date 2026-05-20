package com.sigma.scm.service;

import com.sigma.scm.domain.*;
import com.sigma.scm.repository.DailyDemandStatsRepository;
import com.sigma.scm.repository.ProductFinancialMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.time.LocalDate;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

public class IntegrityServiceTest {

    @Mock
    private RegionInventoryRepository regionInventoryRepository;

    @Mock
    private DailyDemandStatsRepository dailyDemandStatsRepository;

    @Mock
    private ProductFinancialMasterRepository productFinancialMasterRepository;

    @InjectMocks
    private IntegrityService integrityService;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testVerifyStockIntegrityPerfectMatch() {
        String regionCode = "KR-SOUTH";
        String productName = "Mask";
        LocalDate targetDate = LocalDate.of(2026, 5, 20);

        RegionInventory yesterdayInv = new RegionInventory();
        yesterdayInv.setQuantity(500.0);

        RegionInventory todayInv = new RegionInventory();
        todayInv.setQuantity(400.0);

        when(regionInventoryRepository.findById(new RegionInventoryId(regionCode, productName, "2026-05-19")))
                .thenReturn(Optional.of(yesterdayInv));
        when(regionInventoryRepository.findById(new RegionInventoryId(regionCode, productName, "2026-05-20")))
                .thenReturn(Optional.of(todayInv));

        DailyDemandStats stats = new DailyDemandStats();
        stats.setDailyOutboundTotal(100.0);
        when(dailyDemandStatsRepository.findById(new DailyDemandStatsId(regionCode, productName, "2026-05-20")))
                .thenReturn(Optional.of(stats));

        IntegrityService.IntegrityResult result = integrityService.verifyStockIntegrity(regionCode, productName, targetDate);

        assertFalse(result.isHasDiscrepancy());
        assertEquals(0.0, result.getShrinkageQty());
        assertEquals("전산 장부 재고 변동과 트랜잭션 출고 로그가 완벽히 일치하여 데이터 무결성이 검증되었습니다.", result.getMessage());
    }

    @Test
    public void testVerifyStockIntegrityDiscrepancy() {
        String regionCode = "KR-SOUTH";
        String productName = "Mask";
        LocalDate targetDate = LocalDate.of(2026, 5, 20);

        RegionInventory yesterdayInv = new RegionInventory();
        yesterdayInv.setQuantity(500.0);

        RegionInventory todayInv = new RegionInventory();
        todayInv.setQuantity(350.0);

        when(regionInventoryRepository.findById(new RegionInventoryId(regionCode, productName, "2026-05-19")))
                .thenReturn(Optional.of(yesterdayInv));
        when(regionInventoryRepository.findById(new RegionInventoryId(regionCode, productName, "2026-05-20")))
                .thenReturn(Optional.of(todayInv));

        DailyDemandStats stats = new DailyDemandStats();
        stats.setDailyOutboundTotal(100.0);
        when(dailyDemandStatsRepository.findById(new DailyDemandStatsId(regionCode, productName, "2026-05-20")))
                .thenReturn(Optional.of(stats));

        ProductFinancialMaster fin = new ProductFinancialMaster();
        fin.setProductName(productName);
        fin.setUnitPrice(1000);
        when(productFinancialMasterRepository.findById(productName)).thenReturn(Optional.of(fin));

        IntegrityService.IntegrityResult result = integrityService.verifyStockIntegrity(regionCode, productName, targetDate);

        assertTrue(result.isHasDiscrepancy());
        assertEquals(50.0, result.getShrinkageQty());
        assertEquals(50000.0, result.getShrinkageCost());
        assertTrue(result.getMessage().contains("50.0개"));
    }
}
