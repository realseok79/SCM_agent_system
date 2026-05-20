package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "stock_out_logs")
@Data
@NoArgsConstructor
public class StockOutLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "region_code", nullable = false, length = 50)
    private String regionCode;

    @Column(name = "product_name", nullable = false, length = 100)
    private String productName;

    @Column(name = "outbound_qty", nullable = false)
    private Double outboundQty;

    @Column(name = "transaction_type", nullable = false, length = 100)
    private String transactionType = "정상출고";

    @Column(nullable = false)
    private LocalDateTime timestamp = LocalDateTime.now();
}
