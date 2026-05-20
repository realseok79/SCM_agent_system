package com.sigma.scm.repository;

import com.sigma.scm.domain.ProductFinancialMaster;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ProductFinancialMasterRepository extends JpaRepository<ProductFinancialMaster, String> {
}
