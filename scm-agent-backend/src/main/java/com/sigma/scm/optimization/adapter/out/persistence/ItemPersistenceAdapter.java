package com.sigma.scm.optimization.adapter.out.persistence;

import com.sigma.scm.domain.ItemMaster;
import com.sigma.scm.domain.ProductFinancialMaster;
import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.domain.RegionInventoryId;
import com.sigma.scm.optimization.application.port.out.LoadItemPort;
import com.sigma.scm.optimization.domain.model.OptimizationItem;
import com.sigma.scm.repository.ItemMasterRepository;
import com.sigma.scm.repository.ProductFinancialMasterRepository;
import com.sigma.scm.repository.RegionInventoryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Component
@RequiredArgsConstructor
public class ItemPersistenceAdapter implements LoadItemPort {

    private final ItemMasterRepository itemMasterRepository;
    private final ProductFinancialMasterRepository productFinancialMasterRepository;
    private final RegionInventoryRepository regionInventoryRepository;

    @Override
    public Optional<OptimizationItem> loadItem(String productName) {
        Optional<ItemMaster> itemOpt = itemMasterRepository.findById(productName);
        Optional<ProductFinancialMaster> financialOpt = productFinancialMasterRepository.findById(productName);

        if (itemOpt.isPresent() && financialOpt.isPresent()) {
            ItemMaster item = itemOpt.get();
            ProductFinancialMaster financial = financialOpt.get();
            return Optional.of(OptimizationItem.builder()
                    .productName(item.getProductName())
                    .abcClass(item.getAbcClass())
                    .unitPrice(financial.getUnitPrice().doubleValue())
                    .holdingCostRate(item.getHoldingCostRate())
                    .orderingCostFixed(item.getOrderingCostFixed())
                    .baseLeadTimeDays(item.getBaseLeadTimeDays())
                    .build());
        }

        if (financialOpt.isPresent()) {
            ProductFinancialMaster financial = financialOpt.get();
            return Optional.of(OptimizationItem.builder()
                    .productName(financial.getProductName())
                    .abcClass("B")
                    .unitPrice(financial.getUnitPrice().doubleValue())
                    .holdingCostRate(0.2000)
                    .orderingCostFixed(10000.00)
                    .baseLeadTimeDays(3)
                    .build());
        }

        return Optional.empty();
    }

    @Override
    public double loadCurrentStock(String productName, String regionCode) {
        String maxDate = regionInventoryRepository.findMaxDate();
        if (maxDate == null)
            return 0.0;

        RegionInventoryId id = new RegionInventoryId();
        id.setRegionCode(regionCode);
        id.setProductName(productName);
        id.setDate(maxDate);

        return regionInventoryRepository.findById(id)
                .map(RegionInventory::getQuantity)
                .orElse(0.0);
    }

    @Override
    public int countHistoricalSalesDays(String productName, String regionCode) {
        return (int) regionInventoryRepository.findByIdRegionCode(regionCode).stream()
                .filter(inv -> inv.getId().getProductName().equals(productName))
                .map(inv -> inv.getId().getDate())
                .distinct()
                .count();
    }

    @Override
    public double loadDailyAverageDemand(String productName, String regionCode) {
        List<RegionInventory> histories = regionInventoryRepository.findByIdRegionCode(regionCode).stream()
                .filter(inv -> inv.getId().getProductName().equals(productName))
                .collect(Collectors.toList());
        if (histories.isEmpty()) {
            return 0.0;
        }
        double sum = histories.stream().mapToDouble(RegionInventory::getQuantity).sum();
        return sum / histories.size();
    }

    @Override
    public List<Double> loadRecentSales(String productName, String regionCode, int limit) {
        return regionInventoryRepository.findByIdRegionCode(regionCode).stream()
                .filter(inv -> inv.getId().getProductName().equals(productName))
                .sorted((a, b) -> b.getId().getDate().compareTo(a.getId().getDate()))
                .limit(limit)
                .map(RegionInventory::getQuantity)
                .collect(Collectors.toList());
    }
}
