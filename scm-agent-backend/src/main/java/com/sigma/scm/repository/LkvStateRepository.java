package com.sigma.scm.repository;

import com.sigma.scm.domain.LkvState;
import com.sigma.scm.domain.LkvStateId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface LkvStateRepository extends JpaRepository<LkvState, LkvStateId> {
    List<LkvState> findByIdCompanyId(String companyId);
}
