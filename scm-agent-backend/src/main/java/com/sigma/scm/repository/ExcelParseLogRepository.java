package com.sigma.scm.repository;

import com.sigma.scm.domain.ExcelParseLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ExcelParseLogRepository extends JpaRepository<ExcelParseLog, Long> {
    List<ExcelParseLog> findByImportBatchId(String importBatchId);
    void deleteByImportBatchId(String importBatchId);

    @Modifying
    @Transactional
    @Query("DELETE FROM ExcelParseLog l WHERE l.createdAt < :cutoff")
    int deleteOlderThan(@Param("cutoff") LocalDateTime cutoff);
}
