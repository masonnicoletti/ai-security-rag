# Retrieval milestone: 5 example queries

Index `minilm:struct-v1` (2307 chunks), FAISS HNSW (M=32, efSearch=64), top-5. ATLAS release 2026.10.
Each hit shows its chunk_id and the source document it cites.

## 1. Understanding attacks

> What is LLM prompt injection, and how does indirect injection differ from direct injection?

HNSW search 0.32 ms; 5/5 of these are also in exact top-5.

| rank | score | source document | chunk type | chunk_id |
|---|---|---|---|---|
| 1 | 0.744 | [atlas:AML.T0051](https://atlas.mitre.org/techniques/AML.T0051) LLM Prompt Injection (technique) | overview | `atlas:AML.T0051@2026.10#struct-v1:0000` |
| 2 | 0.741 | [atlas:AML.T0051.000](https://atlas.mitre.org/techniques/AML.T0051.000) Direct (technique) | overview | `atlas:AML.T0051.000@2026.10#struct-v1:0000` |
| 3 | 0.714 | [atlas:AML.T0051](https://atlas.mitre.org/techniques/AML.T0051) LLM Prompt Injection (technique) | overview | `atlas:AML.T0051@2026.10#struct-v1:0001` |
| 4 | 0.688 | [atlas:AML.T0051.002](https://atlas.mitre.org/techniques/AML.T0051.002) Triggered (technique) | overview | `atlas:AML.T0051.002@2026.10#struct-v1:0000` |
| 5 | 0.624 | [atlas:AML.T0051.001](https://atlas.mitre.org/techniques/AML.T0051.001) Indirect (technique) | overview | `atlas:AML.T0051.001@2026.10#struct-v1:0000` |

<details><summary>chunk text</summary>

**#1** `atlas:AML.T0051@2026.10#struct-v1:0000`

```
LLM Prompt Injection (AML.T0051) | ATLAS technique
An adversary may craft malicious prompts as inputs to an LLM that cause the LLM to act in unintended ways. These "prompt injections" are often designed to cause the model to ignore aspects of its original instructions and follow the adversary's instructions instead. Prompt Injections can be an initial access vector to the LLM that provides the adversary with a foothold to carry out other steps in their operation. They may be designed to bypass defenses in the LLM, or allow the adversary to issue privileged commands. The effects of a prompt injection can persist throughout an interactive session with an LLM. Malicious prompts may be injected directly by the adversary (Direct (AML.T0051.000)) either to leverage the LLM to generate harmful content or to gain a foothold on the system and lead to further effects. Prompts may also be injected indirectly when the LLM, as part of its normal operation, ingests the malicious prompt from another data source (Indirect (AML.T0051.001)).
```

**#2** `atlas:AML.T0051.000@2026.10#struct-v1:0000`

```
LLM Prompt Injection: Direct (AML.T0051.000) | ATLAS technique
An adversary may inject prompts directly as a user of the LLM. This type of injection may be used by the adversary to gain a foothold in the system or to misuse the LLM itself, as for example to generate harmful content.
Sub-technique of LLM Prompt Injection (AML.T0051). Tactics: Execution (AML.TA0005). Platforms: Generative AI, Agentic AI. Maturity: Realized.
```

**#3** `atlas:AML.T0051@2026.10#struct-v1:0001`

```
LLM Prompt Injection (AML.T0051) | ATLAS technique
Prompts may also be injected indirectly when the LLM, as part of its normal operation, ingests the malicious prompt from another data source (Indirect (AML.T0051.001)). This type of injection can be used by the adversary to gain a foothold on the system or to target the user of the LLM. Malicious prompts may also be Triggered (AML.T0051.002) by user actions or system events. Tactics: Execution (AML.TA0005). Platforms: Generative AI, Agentic AI. Maturity: Realized.
```

**#4** `atlas:AML.T0051.002@2026.10#struct-v1:0000`

```
LLM Prompt Injection: Triggered (AML.T0051.002) | ATLAS technique
An adversary may trigger a prompt injection via a user action or event that occurs within the victim's environment. Triggered prompt injections often target AI agents, which can be activated by means the adversary identifies during Discovery (AML.TA0008) (See Activation Triggers (AML.T0084.002)). These malicious prompts may be hidden or obfuscated from the user and may already exist somewhere in the victim's environment from the adversary performing Prompt Infiltration via Public-Facing Application (AML.T0093). This type of injection may be used by the adversary to gain a foothold in the system or to target an unwitting user of the system.
Sub-technique of LLM Prompt Injection (AML.T0051). Tactics: Execution (AML.TA0005). Platforms: Agentic AI. Maturity: Demonstrated.
```

**#5** `atlas:AML.T0051.001@2026.10#struct-v1:0000`

```
LLM Prompt Injection: Indirect (AML.T0051.001) | ATLAS technique
An adversary may inject prompts indirectly via a separate data channel that the LLM or AI agent ingests, such as text or multimedia pulled from documents, emails, databases or websites. These instructions originate from adversary-controlled content rather than the legitimate user, and are frequently hidden or obfuscated (See LLM Prompt Obfuscation (AML.T0068)) from the user, for example as invisible text. Adversaries may use this to hijack an agent or LLM in order to gain a foothold in the target system or to act against an unwitting user of that system, inheriting whatever privileges the AI system holds. Adversaries may also stage the lure that causes the content to be reached (See AI Agent Clickbait (AML.T0100)), or use the resulting foothold to establish persistence (See AI Agent Context Poisoning (AML.T0080)).
```

</details>

## 2. Defending systems

> What mitigations does ATLAS recommend against model extraction through an API?

HNSW search 0.19 ms; 5/5 of these are also in exact top-5.

| rank | score | source document | chunk type | chunk_id |
|---|---|---|---|---|
| 1 | 0.663 | [atlas:AML.TA0000](https://atlas.mitre.org/tactics/AML.TA0000) AI Model Access (tactic) | links | `atlas:AML.TA0000@2026.10#struct-v1:0001` |
| 2 | 0.640 | [atlas:AML.T0044](https://atlas.mitre.org/techniques/AML.T0044) Full AI Model Access (technique) | links | `atlas:AML.T0044@2026.10#struct-v1:0001` |
| 3 | 0.632 | [atlas:AML.TA0009](https://atlas.mitre.org/tactics/AML.TA0009) Collection (tactic) | links | `atlas:AML.TA0009@2026.10#struct-v1:0002` |
| 4 | 0.628 | [atlas:AML.T0085.003](https://atlas.mitre.org/techniques/AML.T0085.003) System Instructions (technique) | links | `atlas:AML.T0085.003@2026.10#struct-v1:0001` |
| 5 | 0.608 | [atlas:AML.T0137.003](https://atlas.mitre.org/techniques/AML.T0137.003) Extract Memorized Data (technique) | links | `atlas:AML.T0137.003@2026.10#struct-v1:0001` |

<details><summary>chunk text</summary>

**#1** `atlas:AML.TA0000@2026.10#struct-v1:0001`

```
AI Model Access (AML.TA0000) | ATLAS tactic | related ATLAS objects
Techniques for this tactic: AI Model Inference API Access (AML.T0040); Physical Environment Access (AML.T0041); Full AI Model Access (AML.T0044); AI-Enabled Product or Service (AML.T0047).
```

**#2** `atlas:AML.T0044@2026.10#struct-v1:0001`

```
Full AI Model Access (AML.T0044) | ATLAS technique | related ATLAS objects
Mitigated by: Control Access to AI Models and Data at Rest (AML.M0005); AI Model Distribution Methods (AML.M0017).
Used in case studies: Backdoor Attack on Deep Learning Models in Mobile Apps (AML.CS0013); Organization Confusion on Hugging Face (AML.CS0027); AI Model Tampering via Supply Chain Attack (AML.CS0028); Google Photos AI Model Extraction (AML.CS0058).
```

**#3** `atlas:AML.TA0009@2026.10#struct-v1:0002`

```
Collection (AML.TA0009) | ATLAS tactic | related ATLAS objects
Training Data Information from AI Models: Infer Membership (AML.T0137.000); Training Data Information from AI Models: Infer Properties (AML.T0137.001); Training Data Information from AI Models: Invert AI Model (AML.T0137.002); Training Data Information from AI Models: Extract Memorized Data (AML.T0137.003); Recover AI Model Internals (AML.T0144).
```

**#4** `atlas:AML.T0085.003@2026.10#struct-v1:0001`

```
Data from AI Services: System Instructions (AML.T0085.003) | ATLAS technique | related ATLAS objects
Mitigated by: Validate AI Model (AML.M0008); Generative AI Guardrails (AML.M0020); Generative AI Guidelines (AML.M0021); Generative AI Model Alignment (AML.M0022); AI Red Team (AML.M0035).
```

**#5** `atlas:AML.T0137.003@2026.10#struct-v1:0001`

```
Training Data Information from AI Models: Extract Memorized Data (AML.T0137.003) | ATLAS technique | related ATLAS objects
Mitigated by: Validate AI Model (AML.M0008); Generative AI Guardrails (AML.M0020); Adaptive AI Response Degradation (AML.M0040); Privacy-Preserving AI Training and Inference (AML.M0041).
```

</details>

## 3. Real-world evidence

> Which documented incidents involved evading a malware classifier?

HNSW search 0.13 ms; 5/5 of these are also in exact top-5.

| rank | score | source document | chunk type | chunk_id |
|---|---|---|---|---|
| 1 | 0.536 | [atlas:AML.CS0002](https://atlas.mitre.org/studies/AML.CS0002) VirusTotal Poisoning (case-study) | procedure-step | `atlas:AML.CS0002@2026.10#struct-v1:0003` |
| 2 | 0.536 | [atlas:AML.CS0000](https://atlas.mitre.org/studies/AML.CS0000) Evasion of Deep Learning Detector for Malware C&C Traffic (case-study) | procedure-step | `atlas:AML.CS0000@2026.10#struct-v1:0006` |
| 3 | 0.527 | [atlas:AML.T0043.003](https://atlas.mitre.org/techniques/AML.T0043.003) Manual Modification (technique) | links | `atlas:AML.T0043.003@2026.10#struct-v1:0001` |
| 4 | 0.522 | [atlas:AML.CS0002](https://atlas.mitre.org/studies/AML.CS0002) VirusTotal Poisoning (case-study) | overview | `atlas:AML.CS0002@2026.10#struct-v1:0000` |
| 5 | 0.521 | [atlas:AML.T0097](https://atlas.mitre.org/techniques/AML.T0097) Virtualization/Sandbox Evasion (technique) | links | `atlas:AML.T0097@2026.10#struct-v1:0002` |

<details><summary>chunk text</summary>

**#1** `atlas:AML.CS0002@2026.10#struct-v1:0003`

```
VirusTotal Poisoning (AML.CS0002) | ATLAS case study | procedure step S01
In case study VirusTotal Poisoning, step S01 (tactic: AI Attack Adaptation) used technique Craft Adversarial Data (AML.T0043). The actor used a malware sample from a prevalent ransomware family as a start to create "mutant" variants.
```

**#2** `atlas:AML.CS0000@2026.10#struct-v1:0006`

```
Evasion of Deep Learning Detector for Malware C&C Traffic (AML.CS0000) | ATLAS case study | procedure step S05
In case study Evasion of Deep Learning Detector for Malware C&C Traffic, step S05 (tactic: Defense Evasion) used technique Evade AI Model (AML.T0015). With the crafted samples, we performed online evasion of the ML-based spyware detection model. The crafted packets were identified as benign with > 80% confidence. This evaluation demonstrates that adversaries are able to bypass advanced ML detection techniques, by crafting samples that are misclassified by an ML model.
```

**#3** `atlas:AML.T0043.003@2026.10#struct-v1:0001`

```
Craft Adversarial Data: Manual Modification (AML.T0043.003) | ATLAS technique | related ATLAS objects
Mitigated by: Predictive AI Model Hardening (AML.M0003); Limit AI Service Query Volume and Rate (AML.M0004); Predictive AI Ensembles (AML.M0006); Predictive AI Input Restoration (AML.M0010); Predictive AI Adversarial Input Detection (AML.M0015).
Used in case studies: Evasion of Deep Learning Detector for Malware C&C Traffic (AML.CS0000); Bypassing Cylance's AI Malware Detection (AML.CS0003); Attempted Evasion of ML Phishing Webpage Detection System (AML.CS0032).
```

**#4** `atlas:AML.CS0002@2026.10#struct-v1:0000`

```
VirusTotal Poisoning (AML.CS0002) | ATLAS case study
McAfee Advanced Threat Research noticed an increase in reports of a certain ransomware family that was out of the ordinary. Case investigation revealed that many samples of that particular ransomware family were submitted through a popular virus-sharing platform within a short amount of time. Further investigation revealed that based on string similarity the samples were all equivalent, and based on code similarity they were between 98 and 74 percent similar. Interestingly enough, the compile time was the same for all the samples. After more digging, researchers discovered that someone used 'metame' a metamorphic code manipulating tool to manipulate the original file towards mutant variants. The variants would not always be executable, but are still classified as the same ransomware family.
Case study type: Incident. Actor: Unknown. Target: VirusTotal. Reporter: McAfee Advanced Threat Research. Start date: 2020-01-01.
```

**#5** `atlas:AML.T0097@2026.10#struct-v1:0002`

```
Virtualization/Sandbox Evasion (AML.T0097) | ATLAS technique | related ATLAS objects
Used in case studies: Malware Prototype with Embedded Prompt Injection (AML.CS0043).
```

</details>

## 4. Threat modeling

> My app retrieves documents from a shared wiki and passes them to an LLM that can send emails. What attacks should I consider?

HNSW search 0.12 ms; 5/5 of these are also in exact top-5.

| rank | score | source document | chunk type | chunk_id |
|---|---|---|---|---|
| 1 | 0.498 | [atlas:AML.CS0036](https://atlas.mitre.org/studies/AML.CS0036) AIKatz: Attacking LLM Desktop Applications (case-study) | procedure-step | `atlas:AML.CS0036@2026.10#struct-v1:0005` |
| 2 | 0.493 | [atlas:AML.CS0036](https://atlas.mitre.org/studies/AML.CS0036) AIKatz: Attacking LLM Desktop Applications (case-study) | procedure-step | `atlas:AML.CS0036@2026.10#struct-v1:0011` |
| 3 | 0.490 | [atlas:AML.CS0036](https://atlas.mitre.org/studies/AML.CS0036) AIKatz: Attacking LLM Desktop Applications (case-study) | overview | `atlas:AML.CS0036@2026.10#struct-v1:0000` |
| 4 | 0.480 | [atlas:AML.CS0036](https://atlas.mitre.org/studies/AML.CS0036) AIKatz: Attacking LLM Desktop Applications (case-study) | procedure-step | `atlas:AML.CS0036@2026.10#struct-v1:0012` |
| 5 | 0.474 | [atlas:AML.CS0036](https://atlas.mitre.org/studies/AML.CS0036) AIKatz: Attacking LLM Desktop Applications (case-study) | procedure-step | `atlas:AML.CS0036@2026.10#struct-v1:0010` |

<details><summary>chunk text</summary>

**#1** `atlas:AML.CS0036@2026.10#struct-v1:0005`

```
AIKatz: Attacking LLM Desktop Applications (AML.CS0036) | ATLAS case study | procedure step S03
In case study AIKatz: Attacking LLM Desktop Applications, step S03 (tactic: Lateral Movement) used technique Use Alternate Authentication Material: Application Access Token (AML.T0091.000). The attacker used the extracted token to authenticate themselves with the LLM backend service.
```

**#2** `atlas:AML.CS0036@2026.10#struct-v1:0011`

```
AIKatz: Attacking LLM Desktop Applications (AML.CS0036) | ATLAS case study | procedure step S09
In case study AIKatz: Attacking LLM Desktop Applications, step S09 (tactic: Impact) used technique External Harms: Financial Harm (AML.T0048.000). The attacker could send spam messages while impersonating the victim. On a pay-per-token or action plans, this could increase the financial burden on the victim.
```

**#3** `atlas:AML.CS0036@2026.10#struct-v1:0000`

```
AIKatz: Attacking LLM Desktop Applications (AML.CS0036) | ATLAS case study
Researchers at Lumia have demonstrated that it is possible to extract authentication tokens from the memory of LLM Desktop Applications. An attacker could then use those tokens to impersonate the victim to the LLM backend, thereby gaining access to the victim's conversations as well as the ability to interfere in future conversations. The attacker's access would allow them the ability to directly inject prompts to change the LLM's behavior, poison the LLM's context to have persistent effects, manipulate the user's conversation history to cover their tracks, and ultimately impact the confidentiality, integrity, and availability of the system. The researchers demonstrated this on Anthropic Claude, Microsoft M365 Copilot, and OpenAI ChatGPT. Vendor Responses to Responsible Disclosure: - Anthropic (HackerOne) - Closed as informational since local attack. - Microsoft Security Response Center - Attack doesn't bypass security boundaries for CVE.
```

**#4** `atlas:AML.CS0036@2026.10#struct-v1:0012`

```
AIKatz: Attacking LLM Desktop Applications (AML.CS0036) | ATLAS case study | procedure step S10
In case study AIKatz: Attacking LLM Desktop Applications, step S10 (tactic: Impact) used technique External Harms: User Harm (AML.T0048.003). The attacker could gain access to all of the victim's activity with the LLM, including previous and ongoing chats, as well as any file or content uploaded to them.
```

**#5** `atlas:AML.CS0036@2026.10#struct-v1:0010`

```
AIKatz: Attacking LLM Desktop Applications (AML.CS0036) | ATLAS case study | procedure step S08
In case study AIKatz: Attacking LLM Desktop Applications, step S08 (tactic: Defense Evasion) used technique Manipulate User LLM Chat History (AML.T0092). Many LLM desktop applications do not show the injected prompt for any ongoing chat, as they update chat history only once when initially opening it. This gave the attacker the opportunity to cover their tracks by manipulating the user's conversation history directly via the LLM's API. The attacker could also overwrite or delete messages to prevent detection of their actions.
```

</details>

## 5. Identifier lookup

> What does AML.T0051 cover?

HNSW search 0.19 ms; 5/5 of these are also in exact top-5.

| rank | score | source document | chunk type | chunk_id |
|---|---|---|---|---|
| 1 | 0.530 | [atlas:AML.M0016](https://atlas.mitre.org/mitigations/AML.M0016) Vulnerability Scanning (mitigation) | mitigates | `atlas:AML.M0016@2026.10#struct-v1:0001` |
| 2 | 0.527 | [atlas:AML.E0035](https://atlas.mitre.org/entities/AML.E0035) Radware (entity) | overview | `atlas:AML.E0035@2026.10#struct-v1:0000` |
| 3 | 0.526 | [atlas:AML.M0016](https://atlas.mitre.org/mitigations/AML.M0016) Vulnerability Scanning (mitigation) | mitigates | `atlas:AML.M0016@2026.10#struct-v1:0003` |
| 4 | 0.514 | [atlas:AML.M0016](https://atlas.mitre.org/mitigations/AML.M0016) Vulnerability Scanning (mitigation) | mitigates | `atlas:AML.M0016@2026.10#struct-v1:0005` |
| 5 | 0.513 | [atlas:AML.M0042](https://atlas.mitre.org/mitigations/AML.M0042) Threat Intelligence Program (mitigation) | mitigates | `atlas:AML.M0042@2026.10#struct-v1:0006` |

<details><summary>chunk text</summary>

**#1** `atlas:AML.M0016@2026.10#struct-v1:0001`

```
Vulnerability Scanning (AML.M0016) | ATLAS mitigation
Mitigation Vulnerability Scanning (AML.M0016) against technique User Execution (AML.T0011): Vulnerability scanning can help identify malicious binaries and prevent user execution.
```

**#2** `atlas:AML.E0035@2026.10#struct-v1:0000`

```
Radware (AML.E0035) | ATLAS entity
Radware (AML.E0035) is an Israeli cybersecurity company. They protect infrastructure, applications, and corporate IT across physical, cloud, and software-defined data centers. Their products and services help enterprises maintain security, application availability, and business continuity.
Entity type: Organization.
```

**#3** `atlas:AML.M0016@2026.10#struct-v1:0003`

```
Vulnerability Scanning (AML.M0016) | ATLAS mitigation
Mitigation Vulnerability Scanning (AML.M0016) against technique User Execution: Malicious Package (AML.T0011.001): Vulnerability scanning can help identify malicious packages and prevent user execution.
```

**#4** `atlas:AML.M0016@2026.10#struct-v1:0005`

```
Vulnerability Scanning (AML.M0016) | ATLAS mitigation
Mitigation Vulnerability Scanning (AML.M0016) against technique Exploitation for Defense Evasion (AML.T0107): Vulnerability scanning reduces opportunities for adversaries to exploit weaknesses that bypass security controls.
```

**#5** `atlas:AML.M0042@2026.10#struct-v1:0006`

```
Threat Intelligence Program (AML.M0042) | ATLAS mitigation
Mitigation Threat Intelligence Program (AML.M0042) against technique Supply Chain Compromise: Hardware (AML.T0010.000): Collect, analyze, and share intelligence on compromised hardware suppliers and products, including affected models and production batches where known. Use this intelligence to identify affected hardware, prevent its introduction into downstream systems, and prioritize investigation and replacement.
```

</details>
