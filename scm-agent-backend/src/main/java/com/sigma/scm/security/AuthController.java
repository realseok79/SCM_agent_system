package com.sigma.scm.security;

import com.sigma.scm.security.dto.JwtResponse;
import com.sigma.scm.security.dto.LoginRequest;
import com.sigma.scm.security.dto.RefreshTokenRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@CrossOrigin // CORS 정책은 SecurityConfig 및 배포 인프라와 연계
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<JwtResponse> login(@Valid @RequestBody LoginRequest request) {
        JwtResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    public ResponseEntity<JwtResponse> refresh(@Valid @RequestBody RefreshTokenRequest request) {
        JwtResponse response = authService.refresh(request);
        return ResponseEntity.ok(response);
    }
}
