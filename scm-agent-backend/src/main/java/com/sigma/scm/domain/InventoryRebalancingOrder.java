package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "inventory_rebalancing_orders")
@Data
@NoArgsConstructor
public class InventoryRebalancingOrder {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "transfer_id")
    private Long transferId;

    @Column(name = "product_name", nullable = false, length = 100)
    private String productName;

    @Column(name = "from_region", nullable = false, length = 50)
    private String fromRegion;

    @Column(name = "to_region", nullable = false, length = 50)
    private String toRegion;

    @Column(name = "transfer_qty", nullable = false)
    private Integer transferQty;

    @Column(name = "saved_cost", nullable = false)
    private Integer savedCost;

    @Column(length = 50)
    private String status = "PENDING";

    @Column(length = 255)
    private String reason;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
