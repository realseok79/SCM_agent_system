package com.sigma.scm.repository;

import com.sigma.scm.domain.ExcelParseLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ExcelParseLogRepository extends JpaRepository<ExcelParseLog, Long> {
    List<ExcelParseLog> findByImportBatchId(String importBatchId);
    void deleteByImportBatchId(String importBatchId);
}
