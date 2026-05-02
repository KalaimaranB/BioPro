# 🤖 Grogu AI: The BioPro Research Assistant

BioPro features an integrated AI Research Assistant, personified as **Grogu**. Designed to bridge the gap between complex raw data and scientific reasoning, Grogu provides contextual insights, helps navigate workflows, and explains mathematical transformations in real-time.

---

## 🌟 Key Capabilities

- **Context-Aware Reasoning**: Grogu analyzes your active workspace, including loaded plugins and selected documentation files, to provide relevant answers.
- **Protocol Guidance**: Ask about standard lab protocols (e.g., "How should I set my gating thresholds for CD4+ cells?") and get answers based on BioPro's internal knowledge base.
- **Mathematical Transparency**: Grogu can explain the "why" behind BioPro's rendering engines, such as rank-percentile normalization or Gaussian smoothing.
- **Theme-Aware Personality**: Grogu adapts to your UI. In the "Imperial" theme, expect a more disciplined "Droid Mode" personality, while the "Light Side" theme reveals a more helpful, curious assistant.

---

## 📂 Managing Context (The Context Panel)

To ensure high-fidelity reasoning, BioPro uses a **mathematically grounded context window** (capped at 20,000 characters). You can control exactly what information Grogu sees using the **Context Panel** in the AI Chat window.

### 🏛 Core System Docs
By default, Grogu has access to the BioPro core manuals. You can toggle specific files like `User Guide` or `Troubleshooting` to optimize the context window for your current task.

### 🔌 Plugin Documentation
When you are working within a specific module (like Flow Cytometry), the Context Panel automatically discovers and displays documentation unique to that plugin. 

> [!TIP]
> **Optimize Your Queries**: If Grogu seems confused, try unchecking irrelevant core docs and ensuring the specific Plugin documentation is selected.

---

## ⚡ Droid Mode & Themes

BioPro's AI is deeply integrated with the [**Global Theme Engine**](11_Core_Nervous_System.md). 

| Theme | AI Personality | Visual Accents |
| :--- | :--- | :--- |
| **Light Side** | Helpful, curious assistant. | Standard Grogu animations. |
| **Dark Side** | Mysterious, minimalist. | Holographic scan-line effects. |
| **Imperial** | **Droid Mode**: Technical, efficient. | Aurebesh-inspired text and tactical feedback. |

---

## 🛠 Technical Specifications

- **Retrieval Logic**: Uses keyword-based relevance ranking to pull the most important snippets from selected docs.
- **Safety**: The AI server runs locally or via secure verified endpoints, ensuring your raw lab data never leaves your controlled environment.
- **Memory**: Every chat session is isolated; Grogu "forgets" the specifics when the project is closed to maintain data privacy.

---

> [!IMPORTANT]
> **Verification Badge**: Always look for the 🛡 verified badge in the AI interface to ensure you are communicating with the official BioPro service.
