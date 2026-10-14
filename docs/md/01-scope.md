# Stage 1 Document: Requirements Specification and Project Scope

**Engineering Project Documentation**  
**Faculty of Mathematics and Information Science**  
**Warsaw University of Technology**  

---

## 1. Document Metadata and Change History

|    Version    |    Date    |     Author     | Description of Change                                 |
| :-----------: | :--------: | :------------: | :---------------------------------------------------- |
| **1.0** | 15.10.2024 | Alice Kowalska | Baseline version for supervisor sign-off              |
| **1.1** | 18.10.2024 |   Bob Nowak   | Added quantifiable non-functional requirements (NFRs) |

* **Project Title:** *A System for Reconstructing Fragmented Documents Based on the Shape and Content of Their Parts*
* **Authors:** Martyna Sadowska, Hanna Szczerbińska, Zuzanna Zalewska
* **Supervisor:** Janusz Rafałko, Ph.D.

---

## 2. One-Sentence Engineering / Research Problem Formulation

> *“The objective of this project is to design, implement, and evaluate a system capable of reconstructing fragmented (shredded or torn) documents based on an image of their pieces, supported by a dedicated document-splitting module.”*

---

## 3. Project Scope: MVP vs. Future Work (Scope Management)

### 3.1. Minimum Viable Product (MVP – Passing Scope)

1. **Document Splitting Module (Module 1):** 
   - Supports single and batch mode processing.
   - Allows users to split document images using various algorithms, preview piece borders, re-generate if needed, and apply random rotations and non-overlapping background placement.
   - Saves the generated fragments locally.
2. **Document Reconstruction Module (Module 2):**
   - Extracts individual fragments from an input image (single or batch mode).
   - Reconstructs original documents using user-selected or automated algorithms.
   - Displays the reconstructed output, allows iterative improvement (adjusting time or algorithm), and saves the final result locally.

### 3.2. Out of Scope (Future Work)

1. Integration with external cloud storage providers or dedicated mobile applications.
2. Reconstruction of documents with missing fragments.


---

## 4. Functional Requirements (User Stories & Acceptance Criteria)
 
### **US-01: Loading a document image for splitting**
 
* **As a:** User of the document splitting module,
* **I want to:** Upload a single document image or select a folder of document images,
* **So that:** The system can process them for fragment generation.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** The splitting module is open,
> * **When:** The user uploads a valid image file or selects a folder containing valid image files,
> * **Then:** The system loads the images and displays a preview of the first document.
> * **Scenario (Invalid input):**
> * **When:** The user uploads a file in an unsupported format or an empty folder,
> * **Then:** The system displays an error message indicating the accepted formats.
 
---
 
### **US-02: Splitting a document into fragments**
 
* **As a:** User of the document splitting module,
* **I want to:** Select a splitting algorithm and its parameters and preview the proposed piece borders overlaid on the document,
* **So that:** I can control how the document is fragmented.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** A document image has been loaded,
> * **When:** The user selects a splitting algorithm and confirms its parameters,
> * **Then:** The system displays the proposed piece borders overlaid on the original image.
> * **When:** The user is not satisfied with the result and clicks "Generate again",
> * **Then:** The system generates a new set of borders using the same or modified parameters.
 
---
 
### **US-03: Generating a fragmented image**
 
* **As a:** User of the document splitting module,
* **I want to:** Confirm the generated borders and have the system randomly rotate the pieces and arrange them on a plain background without overlapping,
* **So that:** I get an image of document fragments for testing
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** The user has confirmed a set of piece borders,
> * **When:** The user sets parameters and confirms,
> * **Then:** The system produces an image with all fragments placed on the background without overlap.
> * **When:** The user can save the result to a chosen disk location.
 
---
 
### **US-04: Extracting fragments from an input image**
 
* **As a:** User of the document reconstruction module,
* **I want to:** Upload an image containing document fragments (single or batch mode),
* **So that:** The system extracts individual pieces for reconstruction.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** The reconstruction module is open,
> * **When:** The user uploads a valid image containing non-overlapping fragments,
> * **Then:** The system identifies and extracts all individual fragments from the image.
> * **Scenario (Invalid input):**
> * **When:** The image does not contain identifiable fragments,
> * **Then:** The system displays an appropriate error message.
 
---
 
### **US-05: Reconstructing a document from fragments**
 
* **As a:** User of the document reconstruction module,
* **I want to:** Select a reconstruction algorithm (or let the system choose automatically) and view the reconstructed document,
* **So that:** I can achieve the original document content in a legible form.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** Fragments have been extracted from the input image,
> * **When:** The user selects an algorithm or chooses automatic selection, and starts reconstruction,
> * **Then:** The system displays the reconstructed document image.
 
---
 
### **US-06: Iterative enhancement of reconstruction**
 
* **As a:** User of the document reconstruction module,
* **I want to:** Review the reconstruction result and choose to accept it, continue the same algorithm for more time or switch to a different algorithm,
* **So that:** I can iteratively improve the reconstruction quality.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** A reconstruction result is displayed,
> * **When:** The user selects "Continue" with the current algorithm,
> * **Then:** The system resumes processing.
> * **When:** The user selects "Change algorithm" and picks a new one,
> * **Then:** The system restarts reconstruction with the new algorithm.
> * **When:** The user selects "Accept",
> * **Then:** The system allows saving the result locally.

---

## 5. Quantifiable Non-Functional Requirements (NFRs)
 
| ID | Category | Target Quantifiable Metric | Verification Method |
| :-: | :--- | :--- | :--- |
| **NFR-01** | **Performance (Splitting)** | Splitting a single A4-sized document image into at least 50 fragments completes under 60 seconds. | Automated benchmark script with sample dataset |
| **NFR-02** | **Performance (Reconstruction)** | Reconstruction of a document with at least 50 fragments completes under 60 minutes. | Automated benchmark script with sample dataset |
| **NFR-03** | **Scalability** | The system handles documents split into up to 100 fragments without crashing. | Stress tess |
| **NFR-04** | **Usability** | A user with no prior training can complete a full split-and-reconstruct workflow. | Usability test |
| **NFR-05** | **Error Handling** | 100% of invalid inputs produce a user-friendly error message. | test covering all invalid input scenarios |
| **NFR-06** | **Availability** | The system operates fully offline | Disconnected network test |
| **NFR-07** | **Security** | All image processing is performed locally and no data is transmitted to external servers.  | Manual verification of network traffic |

---

## 6. Glossary

| Term                                      | Definition                                                                                                                                                                                    |
| :---------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **APD (Archiwum Prac Dyplomowych)** | University Thesis Archive; official web portal of Warsaw University of Technology used for thesis submission, anti-plagiarism verification, and archiving.                                    |
| **Hypertable**                      | A TimescaleDB abstraction that presents time-series data as a single continuous PostgreSQL table while transparently partitioning it into time-based chunks under the hood.                   |
| **Isolation Forest**                | An unsupervised machine learning algorithm for anomaly detection that isolates observations by randomly selecting a feature and split value, where anomalies require fewer splits to isolate. |
| **MVP (Minimum Viable Product)**    | The minimal functional scope of the project fulfilling all foundational requirements for academic project evaluation and defense.                                                             |
| **p95 Latency**                     | The 95th percentile of response time distribution, indicating that 95% of all incoming requests are served in less than the specified duration.                                               |
| **Rolling Z-Score**                 | A localized statistical metric representing the number of standard deviations a given observation deviates from the moving mean over a sliding temporal window.                               |
| **Telemetry**                       | Automated remote collection and transmission of operational measurement data from distributed sensors or agents to a central receiving station.                                               |

---

## 7. Preliminary Risk Register and Role Allocation

*(Detailed Risk Register and RACI Matrix are defined in dedicated documents: [`management/risk-register-and-contingency.md`](../management/risk-register-and-contingency.md) and [`management/team-charter-and-raci.md`](../management/team-charter-and-raci.md).)*

---

## 8. Formal Supervisor Acceptance

* [X] **Scope and MVP Sign-off:** The supervisor has reviewed the requirements specification and approves the MVP scope as the foundation for the engineering / master's degree project.

**Supervisor Signature:** ............................................................ **Date:** October 18, 2026
