package com.sigma.scm.repository;

import com.sigma.scm.domain.BatchStatusHistory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface BatchStatusHistoryRepository extends JpaRepository<BatchStatusHistory, Long> {
    List<BatchStatusHistory> findByBatchId(String batchId);

    @Modifying
    @Transactional
    @Query("DELETE FROM BatchStatusHistory h WHERE h.createdAt < :cutoff")
    int deleteOlderThan(@Param("cutoff") LocalDateTime cutoff);
}
