package com.sigma.scm.repository;

import com.sigma.scm.domain.InventoryRebalancingOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface InventoryRebalancingOrderRepository extends JpaRepository<InventoryRebalancingOrder, Long> {
    List<InventoryRebalancingOrder> findByStatus(String status);
}
