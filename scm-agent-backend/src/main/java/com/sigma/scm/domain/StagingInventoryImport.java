package com.sigma.scm.domain;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "staging_inventory_imports")
@Data
@NoArgsConstructor
public class StagingInventoryImport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "import_batch_id", nullable = false, length = 100)
    private String importBatchId;

    @Column(name = "company_id", nullable = false, length = 100)
    private String companyId;

    @Column(name = "region_code", length = 50)
    private String regionCode;

    @Column(name = "product_name", length = 100)
    private String productName;

    @Column(length = 20)
    private String date;

    private Double quantity;

    @Column(name = "validation_status", length = 50)
    private String validationStatus;

    @Column(name = "source_row_index")
    private Integer sourceRowIndex;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();
}
