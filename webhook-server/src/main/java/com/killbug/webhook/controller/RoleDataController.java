package com.killbug.webhook.controller;

import java.util.List;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.killbug.webhook.controller.request.RoleDataCreateRequest;
import com.killbug.webhook.controller.response.RoleDataResponse;
import com.killbug.webhook.exception.Response;
import com.killbug.webhook.service.RoleDataService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/role-data")
@RequiredArgsConstructor
public class RoleDataController {

    private final RoleDataService roleDataService;

    @GetMapping("/{role}")
    public ResponseEntity handleList(@PathVariable String role) {
        List<RoleDataResponse> result =
                switch (role) {
                    case "junior" -> roleDataService.listJunior();
                    case "senior" -> roleDataService.listSenior();
                    case "lead" -> roleDataService.listLead();
                    default -> throw new IllegalArgumentException(
                            "유효하지 않은 역할: " + role + " (junior, senior, lead 중 선택)");
                };
        return Response.OK.getApiResponse(result);
    }

    @PostMapping("/{role}")
    public ResponseEntity handleCreate(@PathVariable String role, @RequestBody RoleDataCreateRequest request) {
        RoleDataResponse result =
                switch (role) {
                    case "junior" -> roleDataService.createJunior(request);
                    case "senior" -> roleDataService.createSenior(request);
                    case "lead" -> roleDataService.createLead(request);
                    default -> throw new IllegalArgumentException(
                            "유효하지 않은 역할: " + role + " (junior, senior, lead 중 선택)");
                };
        return Response.OK.getApiResponse(result);
    }
}
