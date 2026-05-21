# BioPro Documentation Portal

Welcome to the official **BioPro Documentation Portal**. BioPro is an open-source biological analysis suite designed for researchers, software developers, and academic institutions.

---

<div class="grid cards" markdown>

-   **User Manuals**
    
    Get started with the interface, wizards, project managers, and the Help Center.
    
    [View User Guides](user/01_User_Guide.md)

-   **Internal Architecture**
    
    Deep-dive into the Event Bus, dynamic loaders, module managers, and the core system.
    
    [View Internal Architecture](internal/11_Core_Nervous_System.md)

-   **Developer Onboarding**
    
    Learn how to build plugins, compile analysis pipelines, and work with the SDK.
    
    [Start Onboarding](internal/19_Developer_Onboarding.md)

-   **Security Spec**
    
    Examine the signature verification implementation and plugin validation policies.
    
    [View Security Spec](internal/21_Supply_Chain_Security.md)

</div>

---

## Key Application Features

### Plugin Ecosystem
BioPro enforces strict plugin validation. A distributed plugin must satisfy signature checks before it is authorized to run inside the host, ensuring data integrity.

### History Management
Every user adjustment is stored as a deterministic state change, letting you step backward or forward through history instantly.

### AI Assistant
An integrated AI Assistant provides contextual help with biological pipelines, navigating workflows, and managing analysis data based on the provided documentation.

---

### Getting Started
If you are new to the platform, jump straight into the installation guides to configure your environment:
*   [Getting Started & Launching](user/02_Getting_Started.md)
*   [Running Your First Analysis Wizard](user/03_Tutorial_First_Analysis.md)
