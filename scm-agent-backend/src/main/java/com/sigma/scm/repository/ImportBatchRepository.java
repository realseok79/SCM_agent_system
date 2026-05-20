package com.sigma.scm.repository;

import com.sigma.scm.domain.ImportBatch;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ImportBatchRepository extends JpaRepository<ImportBatch, String> {
    List<ImportBatch> findByCompanyId(String companyId);
}
