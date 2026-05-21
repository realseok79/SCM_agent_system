package com.sigma.scm.repository;

import com.sigma.scm.domain.IotDevice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface IotDeviceRepository extends JpaRepository<IotDevice, String> {
    List<IotDevice> findByStatus(String status);
}
