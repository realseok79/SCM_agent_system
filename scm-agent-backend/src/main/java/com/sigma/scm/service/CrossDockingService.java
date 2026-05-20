package com.sigma.scm.service;

import com.sigma.scm.domain.InventoryRebalancingOrder;
import com.sigma.scm.domain.ProductFinancialMaster;
import com.sigma.scm.repository.InventoryRebalancingOrderRepository;
import com.sigma.scm.repository.ProductFinancialMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class CrossDockingService {

    private final RegionInventoryRepository regionInventoryRepository;
    private final ProductFinancialMasterRepository productFinancialMasterRepository;
    private final InventoryRebalancingOrderRepository rebalancingOrderRepository;

    public static class RebalanceResult {
        private final double rebalancedQty;
        private final double remainingPoQty;
        private final List<InventoryRebalancingOrder> transfers;

        public RebalanceResult(double rebalancedQty, double remainingPoQty, List<InventoryRebalancingOrder> transfers) {
            this.rebalancedQty = rebalancedQty;
            this.remainingPoQty = remainingPoQty;
            this.transfers = transfers;
        }

        public double getRebalancedQty() { return rebalancedQty; }
        public double getRemainingPoQty() { return remainingPoQty; }
        public List<InventoryRebalancingOrder> getTransfers() { return transfers; }
    }

    @Transactional
    public RebalanceResult attemptCrossDocking(String productName, double requiredQty) {
        String maxDate = regionInventoryRepository.findMaxDate();
        double rebalancedQty = 0.0;
        List<InventoryRebalancingOrder> transfers = new ArrayList<>();

        if (maxDate != null && requiredQty > 0) {
            List<Object[]> candidates = regionInventoryRepository.findCrossDockingCandidates(productName, maxDate);
            
            // Get unit price for cost savings calculation
            int unitPrice = productFinancialMasterRepository.findById(productName)
                    .map(ProductFinancialMaster::getUnitPrice)
                    .orElse(10000);

            for (Object[] candidate : candidates) {
                if (rebalancedQty >= requiredQty) {
                    break;
                }

                String fromRegion = (String) candidate[0];
                double quantity = ((Number) candidate[1]).doubleValue();
                double movingAvg30d = ((Number) candidate[2]).doubleValue();

                // DoS > 90.0 and quantity >= 100.0
                if (movingAvg30d > 0) {
                    double dos = quantity / movingAvg30d;
                    if (dos > 90.0 && quantity >= 100.0) {
                        double surplus = quantity - (movingAvg30d * 90.0);
                        double transferQty = Math.min(surplus, requiredQty - rebalancedQty);

                        if (transferQty > 0) {
                            int transferQtyInt = (int) Math.round(transferQty);
                            if (transferQtyInt > 0) {
                                int savedCost = transferQtyInt * unitPrice;

                                InventoryRebalancingOrder order = new InventoryRebalancingOrder();
                                order.setProductName(productName);
                                order.setFromRegion(fromRegion);
                                order.setToRegion("GLOBAL_ORDER");
                                order.setTransferQty(transferQtyInt);
                                order.setSavedCost(savedCost);
                                order.setStatus("APPROVED");
                                order.setCreatedAt(LocalDateTime.now());

                                rebalancingOrderRepository.save(order);
                                transfers.add(order);

                                rebalancedQty += transferQtyInt;
                            }
                        }
                    }
                }
            }
        }

        double remainingPoQty = Math.max(0.0, requiredQty - rebalancedQty);
        return new RebalanceResult(rebalancedQty, remainingPoQty, transfers);
    }
}
