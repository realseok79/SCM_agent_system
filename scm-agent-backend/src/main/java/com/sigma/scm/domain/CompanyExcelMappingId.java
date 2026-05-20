package com.sigma.scm.domain;

import jakarta.persistence.Embeddable;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

@Embeddable
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CompanyExcelMappingId implements Serializable {
    private String companyId;
    private String rawHeader;
    private String mappedColumn;
}
