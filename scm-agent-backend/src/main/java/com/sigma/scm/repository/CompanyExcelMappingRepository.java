package com.sigma.scm.repository;

import com.sigma.scm.domain.CompanyExcelMapping;
import com.sigma.scm.domain.CompanyExcelMappingId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface CompanyExcelMappingRepository extends JpaRepository<CompanyExcelMapping, CompanyExcelMappingId> {
    List<CompanyExcelMapping> findByIdCompanyId(String companyId);
}
