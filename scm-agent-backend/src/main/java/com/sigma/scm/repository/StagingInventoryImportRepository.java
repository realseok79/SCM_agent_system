package com.sigma.scm.repository;

import com.sigma.scm.domain.StagingInventoryImport;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StagingInventoryImportRepository extends JpaRepository<StagingInventoryImport, Long> {
    List<StagingInventoryImport> findByImportBatchId(String importBatchId);
    void deleteByImportBatchId(String importBatchId);
}
