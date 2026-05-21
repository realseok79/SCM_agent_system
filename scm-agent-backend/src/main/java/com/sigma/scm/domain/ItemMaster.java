package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "item_master")
@Data
@NoArgsConstructor
public class ItemMaster {

    @Id
    @Column(name = "product_name", length = 100)
    private String productName;

    @Column(name = "abc_class", nullable = false, length = 1)
    private String abcClass;

    @Column(name = "holding_cost_rate", nullable = false)
    private Double holdingCostRate = 0.2000;

    @Column(name = "ordering_cost_fixed", nullable = false)
    private Double orderingCostFixed = 10000.00;

    @Column(name = "base_lead_time_days", nullable = false)
    private Integer baseLeadTimeDays = 3;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
