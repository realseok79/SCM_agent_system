package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "product_financial_master")
@Data
@NoArgsConstructor
public class ProductFinancialMaster {

    @Id
    @Column(name = "product_name", length = 100)
    private String productName;

    @Column(name = "unit_price", nullable = false)
    private Integer unitPrice;

    @Column(name = "holding_cost_per_day", nullable = false)
    private Double holdingCostPerDay;
}
