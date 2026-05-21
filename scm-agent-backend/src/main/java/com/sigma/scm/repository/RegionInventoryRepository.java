package com.sigma.scm.repository;

import com.sigma.scm.domain.RegionInventory;
import com.sigma.scm.domain.RegionInventoryId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RegionInventoryRepository extends JpaRepository<RegionInventory, RegionInventoryId> {
    List<RegionInventory> findByIdRegionCode(String regionCode);
    List<RegionInventory> findByIdRegionCodeAndIdDate(String regionCode, String date);
    void deleteBySourceBatchId(String sourceBatchId);

    @org.springframework.data.jpa.repository.Query("SELECT DISTINCT r.id.regionCode FROM RegionInventory r")
    List<String> findDistinctRegionCodes();

    @org.springframework.data.jpa.repository.Query(value = "SELECT MAX(date) FROM region_inventory", nativeQuery = true)
    String findMaxDate();

    @org.springframework.data.jpa.repository.Query(value = "SELECT i.region_code, i.quantity, d.moving_avg_30d " +
            "FROM region_inventory i " +
            "JOIN daily_demand_stats d ON i.region_code = d.region_code AND i.product_name = d.product_name AND i.date = d.date " +
            "WHERE i.product_name = :productName AND i.date = :date", nativeQuery = true)
    List<Object[]> findCrossDockingCandidates(
            @org.springframework.data.repository.query.Param("productName") String productName, 
            @org.springframework.data.repository.query.Param("date") String date);
}

