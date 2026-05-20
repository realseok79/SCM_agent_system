package com.sigma.scm.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EmbeddedId;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "company_excel_mapping")
@Data
@NoArgsConstructor
public class CompanyExcelMapping {

    @EmbeddedId
    private CompanyExcelMappingId id;

    @Column(nullable = false)
    private Double confidence;

    @Column(name = "negative_score", nullable = false)
    private Double negativeScore = 0.0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();
}
