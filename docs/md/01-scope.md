# Stage 1 Document: Requirements Specification and Project Scope

**Engineering Project Documentation**  
**Faculty of Mathematics and Information Science**  
**Warsaw University of Technology**  

---

## 1. Document Metadata and Change History

|    Version    |    Date    |     Author     | Description of Change                                 |
| :-----------: | :--------: | :------------: | :---------------------------------------------------- |
| **1.0** | 13.10.2026 | Zuzanna Zalewska | Baseline version for supervisor sign-off, problem formulation and project scope              |
| **1.1** | 14.10.2026 |   Zuzanna Zalewska   | Added functional non-functional requirements |
| **1.2** | 15.10.2026 | Martyna Sadowska | Added risk register and contingency plans

* **Project Title:** *A System for Reconstructing Fragmented Documents Based on the Shape and Content of Their Parts*
* **Authors:** Martyna Sadowska, Hanna Szczerbińska, Zuzanna Zalewska
* **Supervisor:** Janusz Rafałko, Ph.D.

---

## 2. One-Sentence Engineering / Research Problem Formulation

> *“The objective of this project is to design, implement, and evaluate a system capable of reconstructing fragmented (shredded or torn) documents based on an image of their pieces, as well as artificially splitting a document into such pieces.”*

---

## 3. Project Scope: MVP vs. Future Work (Scope Management)

### 3.1. Minimum Viable Product (MVP – Passing Scope)

1. **Document Splitting Module (Module 1):** 
   - Supports single and batch mode processing.
   - Allows users to split document images using various algorithms, preview piece borders, re-generate if needed, and apply random rotations and non-overlapping background placement.
   - Saves the final image of generated fragments locally.
2. **Document Reconstruction Module (Module 2):**
   - Supports single and batch mode processing.
   - Extracts individual fragments from an input image.
   - Reconstructs original documents using a variety of algorithms.
   - Displays the reconstructed output, allows for iterative improvement (adjusting either the processing time or algorithm used), and saves the final result locally.

### 3.2. Out of Scope (Future Work)

1. Integration with external cloud storage providers or dedicated mobile applications.
2. Reconstruction of documents with missing fragments.
3. Reconstruction of several documents whose fragments are combined. 

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
> * **When:** The user uploads a file in an unsupported format or a file that doesn't contain any valid image files,
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
> * **Then:** The system generates a new set of borders using the currently selected algorithm and its parameters.
 
---
 
### **US-03: Generating a fragmented image**
 
* **As a:** User of the document splitting module,
* **I want to:** Confirm the generated borders and have the system randomly rotate the pieces and arrange them on a plain background without overlapping,
* **So that:** I get an image with document fragments which can later be used for testing the document reconstruction module. 
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** The user has confirmed a set of piece borders,
> * **When:** The user sets the parameters for arranging the pieces and confirms them,
> * **Then:** The system produces an image with all fragments placed on the background without any overlap.
> * **When:** The user selects the option to save the final image and selects a disk location, 
> * **Then:** The result is saved to the chosen disk location.
 
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
* **I want to:** Select a reconstruction algorithm (or let the system choose one automatically) and view the reconstructed document,
* **So that:** I can receive the original document content in a legible form.
 
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
| **NFR-01** | **Performance (Splitting)** | Splitting a single A4-sized document image into at least 20 fragments completes under 60 seconds. | Automated benchmark script with sample dataset |
| **NFR-02** | **Performance (Reconstruction)** | Reconstruction of a document with at least 20 fragments completes under 60 minutes. | Automated benchmark script with sample dataset |
| **NFR-03** | **Scalability** | The system handles documents split into up to 100 fragments without crashing. | Stress tess |
| **NFR-04** | **Usability** | A user with no prior training can complete a full split-and-reconstruct workflow. | Usability test |
| **NFR-05** | **Error Handling** | 100% of invalid inputs produce a user-friendly error message. | Test covering all invalid input scenarios |
| **NFR-06** | **Availability** | The system operates fully offline | Disconnected network test |
| **NFR-07** | **Security** | All image processing is performed locally and no data is transmitted to external servers.  | Manual verification of network traffic |

---

## 6. Glossary

| Term                                      | Definition                                                                                                                                                                                    |
| :---------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **APD (Archiwum Prac Dyplomowych)** | University Thesis Archive; official web portal of Warsaw University of Technology used for thesis submission, anti-plagiarism verification, and archiving.                                    |
| **MVP (Minimum Viable Product)**    | The minimal functional scope of the project fulfilling all foundational requirements for academic project evaluation and defense.                                                             |
| **Module 1**    | The document-splitting module, whose scope includes splitting an image into several fragments and arranging those fragments against a background.                                                              |
| **Module 2**    | The document reconstruction module, whose scope includes extracting individual fragments from an image and reconstructing the original document based on the fragments' shape and content.                                                              |

---

## 7. Preliminary Risk Register and Role Allocation

### 7.1 Project and Technical Risk Register

|        ID        | Risk Event                                                   | Likelihood (L/M/H) | Impact (L/M/H/Crit) |  Owner  | Mitigation Strategy                                                                                                                 |
| :--------------: | :----------------------------------------------------------- | :----------------: | :-----------------: | :------: | :---------------------------------------------------------------------------------------------------------------------------------- |
| **RSK-01** | **Team member illness / drop-out**                     |         L         |          H          | Everyone | Peer code review for every PR, pair programming on the critical path, modular architecture.                                               |
| **RSK-02** | **Insufficient accuracy for the reconstructing algorithm**                     |         M         |          H          | Everyone | Explore different algorithms; if the problem persists focus on an analysis of algorithmic limitations and failure cases. |
| **RSK-03** | **Environment incompatibility in the MiNI laboratory** |         M         |        Crit        | Martyna Sadowska | Test deployment on lab machines after implementing Module 1 and another after Module 2, not the night before acceptance. |
| **RSK-04** | **Hardware failure (loss of data / code on laptop)**   |         M         |        Crit        | Everyone | Pushes to remote repository (GitHub) after each change.                         |
| **RSK-05** | **Thesis writing workload accumulation in January**    |         H         |          H          | Everyone | Incremental drafting of thesis chapters; peer reviews within the team.                          |
| **RSK-06** | **Unacceptably long execution time**                        |         H         |          M          | Hanna Szczerbińska | Implementing early stopping to the algorithms and accepting the worse results.                                 |
| **RSK-07** | **Rotation of the fragments resulting in quality loss and document illegibility.** | M | M | Zuzanna Zalewska | Remembering the fragments' original visual, rotating it only once to match the found rotation and accepting the loss of information resulting in this operation. |
| **RSK-08** | **Loss of information on the edges of fragments as a result of inacurate cut or assembling.** | M | L | Zuzanna Zalewska | Accepting the problem as an opportunity to test the algorithms in a real-world scenario (manual paper shredding). |
| **RSK-09** | **Excessive RAM requirements for running the program smoothly** | M | M | Martyna Sadowska | Switching to the faculty MiNI GPU cluster |
| **RSK-10** | **Excessive hyperparameter tuning time** | M | M | Hanna Szczerbińska | Finding a different algorithm or accepting the suboptimal hyperparameters. |
| **RSK-11** | **No measurable metrics for assessing the accuracy of splitting and reconstructing the document.** | H | M | Zuzanna Zalewska | Relying solely on manual visual assessment. |
| **RSK-12** | **Inability of the chosen UI library to meet our design requirements** | L | L | Martyna Sadowska | UI redesign or library change. |
| **RSK-13** | **To high difficulty of the chosen UI library** | L | L | Martyna Sadowska | Library change. |


---

### 7.1 Contingency Plans for High-Risk Modules (Plan B Protocols)

### **Contingency Protocol 1: Live Demo Failure during Defense**

* **Plan A (Primary):** Run a pre-recorded video demo with live narration during the 10-minute presentation.
* **Plan B Trigger:** Projector connectivity issues, network failure.
* **Plan B (Contingency):** Immediately switch to a presentation with screenshots showcasing the application's core functionality.

### **Contingency Protocol 2: Literature Dataset Issues**

* **Plan A (Primary):** Use existing datasets from literature.
* **Plan B Trigger:** Restricted access to external datasets or unsatisfactory results from them.
* **Plan B (Contingency):** Start constructing a custom dataset by shredding and scanning physical documents.

---

## 8. Formal Supervisor Acceptance

* [X] **Scope and MVP Sign-off:** The supervisor has reviewed the requirements specification and approves the MVP scope as the foundation for the engineering / master's degree project.

**Supervisor Signature:** ............................................................ **Date:** October 18, 2026
