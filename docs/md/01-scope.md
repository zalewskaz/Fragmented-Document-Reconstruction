# Stage 1 Document: Requirements Specification and Project Scope

**Engineering Project Documentation**  
**Faculty of Mathematics and Information Science**  
**Warsaw University of Technology**  


## 1. Document Metadata and Change History

|    Version    |    Date    |     Author     | Description of Change                                 |
| :-----------: | :--------: | :------------: | :---------------------------------------------------- |
| **1.0** | 13.10.2026 | ZZ | Baseline version for supervisor sign-off, problem formulation and project scope              |
| **1.1** | 14.10.2026 | ZZ | Added functional non-functional requirements |
| **1.2** | 15.10.2026 | MS | Added risk register and contingency plans
| **1.3** | 16.10.2026 | HS | Expanded out of scope and glossary sections 
| **1.4** | 18.10.2026 | ZZ | Created schedule
| **1.5** | 19.10.2026 | HS | Assigned roles to RACI matrix
| **1.6** | 20.10.2026 | MS | Added schedule and RACI matrix to the document

* **Project Title:** *A System for Reconstructing Fragmented Documents Based on the Shape and Content of Their Parts*
* **Authors:** Martyna Sadowska (MS), Hanna Szczerbińska (HS), Zuzanna Zalewska (ZZ)
* **Supervisor:** Janusz Rafałko, Ph.D. (JR)


## 2. One-Sentence Engineering / Research Problem Formulation

> *“The objective of this project is to design, implement, and evaluate a system capable of reconstructing fragmented (shredded or torn) documents based on an image of their pieces, as well as artificially splitting a document into such pieces.”*


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
 
 
### **US-05: Reconstructing a document from fragments**
 
* **As a:** User of the document reconstruction module,
* **I want to:** Select a reconstruction algorithm (or let the system choose one automatically) and view the reconstructed document,
* **So that:** I can receive the original document content in a legible form.
 
> **Acceptance Criteria (Gherkin):**
>
> * **Given:** Fragments have been extracted from the input image,
> * **When:** The user selects an algorithm or chooses automatic selection, and starts reconstruction,
> * **Then:** The system displays the reconstructed document image.
 
 
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


## 5. Quantifiable Non-Functional Requirements (NFRs)
 
| ID | Category | Target Quantifiable Metric | Verification Method |
| :- | :--- | :--- | :--- |
| **NFR-01** | **Performance (Splitting)** | Splitting a single A4-sized document image into at least 20 fragments completes under 60 seconds. | Automated benchmark script with sample dataset |
| **NFR-02** | **Performance (Reconstruction)** | Reconstruction of a document with at least 20 fragments completes under 60 minutes. | Automated benchmark script with sample dataset |
| **NFR-03** | **Scalability** | The system handles documents split into up to 100 fragments without crashing. | Stress tess |
| **NFR-04** | **Usability** | A user with no prior training can complete a full split-and-reconstruct workflow. | Usability test |
| **NFR-05** | **Error Handling** | 100% of invalid inputs produce a user-friendly error message. | Test covering all invalid input scenarios |
| **NFR-06** | **Availability** | The system operates fully offline | Disconnected network test |
| **NFR-07** | **Security** | All image processing is performed locally and no data is transmitted to external servers.  | Manual verification of network traffic |


## 6. Preliminary Risk Register

### 6.1 Project and Technical Risk Register

|        ID        | Risk Event                               | Likelihood (L/M/H) | Impact (L/M/ H/Crit) |  Owner | Mitigation Strategy                                                    |
| :----------- | :--------------------------------------- | :---------- | :---------- | :----------- | :----------------------------------------------- |
| **RSK-01** | **Team member illness / drop-out**                     |         L         |          H          | Everyone | Peer code review for every PR, pair programming on the critical path, modular architecture.                                               |
| **RSK-02** | **Insufficient accuracy for the reconstructing algorithm**                     |         M         |          H          | Everyone | Explore different algorithms; if the problem persists focus on an analysis of algorithmic limitations and failure cases. |
| **RSK-03** | **Environment incompatibility in the MiNI laboratory** |         M         |        Crit        | MS | Test deployment on lab machines after implementing Module 1 and another after Module 2, not the night before acceptance. |
| **RSK-04** | **Hardware failure (loss of data / code on laptop)**   |         M         |        Crit        | Everyone | Pushes to remote repository (GitHub) after each change.                         |
| **RSK-05** | **Thesis writing workload accumulation in January**    |         H         |          H          | Everyone | Incremental drafting of thesis chapters; peer reviews within the team.                          |
| **RSK-06** | **Unacceptably long execution time**                        |         H         |          M          | HS | Implementing early stopping to the algorithms and accepting the worse results.                                 |
| **RSK-07** | **Rotation of the fragments resulting in quality loss and document illegibility.** | M | M | ZZ | Remembering the fragments' original visual, rotating it only once to match the found rotation and accepting the loss of information resulting in this operation. |
| **RSK-08** | **Loss of information on the edges of fragments as a result of inacurate cut or assembling.** | M | L | ZZ | Accepting the problem as an opportunity to test the algorithms in a real-world scenario (manual paper shredding). |
| **RSK-09** | **Excessive RAM requirements for running the program smoothly** | M | M | MS | Switching to the faculty MiNI GPU cluster |
| **RSK-10** | **Excessive hyperparameter tuning time** | M | M | HS | Finding a different algorithm or accepting the suboptimal hyperparameters. |
| **RSK-11** | **No measurable metrics for assessing the accuracy of splitting and reconstructing the document.** | H | M | ZZ | Relying solely on manual visual assessment. |
| **RSK-12** | **Inability of the chosen UI library to meet our design requirements** | L | L | MS | UI redesign or library change. |
| **RSK-13** | **To high difficulty of the chosen UI library** | L | L | MS | Library change. |


### 6.2 Contingency Plans for High-Risk Modules (Plan B Protocols)

### **Contingency Protocol 1: Live Demo Failure during Defense**

* **Plan A (Primary):** Run a pre-recorded video demo with live narration during the 10-minute presentation.
* **Plan B Trigger:** Sound system issues, network failure.
* **Plan B (Contingency):** Immediately switch to a presentation with screenshots showcasing the application's core functionality.

### **Contingency Protocol 2: Literature Dataset Issues**

* **Plan A (Primary):** Use existing datasets from literature.
* **Plan B Trigger:** Restricted access to external datasets or unsatisfactory results from them.
* **Plan B (Contingency):** Construct a custom dataset by shredding and scanning physical documents.

## 7. Schedule and Role Allocation

The Gantt Diagram corresponding to the schedule is located in a dedicated document: [schedule_and_tasks_overview.xlsx](https://github.com/zalewskaz/Fragmented-Document-Reconstruction/blob/main/docs/schedule_and_tasks_overview.xlsx). 

### 7.1 Schedule

| WBS   | Task                                                                                         | Duration (Days) | Start Date | End Date  |
|-------|----------------------------------------------------------------------------------------------|-----------------|------------|-----------|
| **1** | **Project Planning & Architecture**                                                          | **13**          | **11-10**  | **23-10** |
| 1.1   | Define business objective                                                                    | 3               | 11-10      | 13-10     |
| 1.2   | Define system vision                                                                         | 3               | 11-10      | 13-10     |
| 1.3   | Define functional requirements                                                               | 4               | 13-10      | 16-10     |
| 1.4   | Define non-functional requirements                                                           | 3               | 14-10      | 16-10     |
| 1.5   | Perform risk analysis                                                                        | 2               | 14-10      | 15-10     |
| 1.6   | Prepare project schedule and divide tasks between team members                               | 4               | 16-10      | 19-10     |
| 1.7   | Decide on the formats in which data will be stored and handled                               | 1               | 16-10      | 16-10     |
| 1.8   | Define system architecture and main classes                                                  | 5               | 19-10      | 23-10     |
| 1.9   | Decide on main dependencies (e.g. external libraries)                                        | 8               | 13-10      | 20-10     |
| 1.10  | Prepare a shortlist of algorithms to be implemented for each module                          | 11              | 13-10      | 23-10     |
| **2** | **Module 1: Document Fragmentation**                                                         | **13**          | **19-10**  | **31-10** |
| 2.1   | Implement input handling                                                                     | 2               | 19-10      | 20-10     |
| 2.2   | Implement fragmentation algorithms                                                           | 10              | 19-10      | 28-10     |
| 2.3   | Implement the random rotation of each fragment                                               | 3               | 21-10      | 23-10     |
| 2.4   | Implement fragment placement on background                                                   | 3               | 21-10      | 23-10     |
| 2.5   | Implement image export                                                                       | 2               | 23-10      | 24-10     |
| 2.6   | Write unit tests for module 1                                                                | 3               | 26-10      | 28-10     |
| 2.7   | Validate results through subjective observation                                              | 9               | 23-10      | 31-10     |
| **3** | **Module 2A: Fragment Extraction**                                                           | **7**           | **1-11**   | **7-11**  |
| 3.1   | Implement the algorithm for finding fragment borders                                         | 4               | 1-11       | 4-11      |
| 3.2   | Implement extracting the fragments into separate objects                                     | 2               | 4-11       | 5-11      |
| 3.3   | Write unit tests for module 2A                                                               | 2               | 6-11       | 7-11      |
| **4** | **Module 2B: Document Reconstruction**                                                       | **17**          | **8-11**   | **24-11** |
| 4.1   | Implement  shape-based reconstruction algorithms                                             | 13              | 8-11       | 20-11     |
| 4.2   | Implement content-based reconstruction algorithms                                            | 13              | 8-11       | 20-11     |
| 4.3   | Write unite tests for module 2B                                                              | 4               | 21-11      | 24-11     |
| **5** | **Benchmarking**                                                                             | **6**           | **25-11**  | **30-11** |
| 5.1   | Implement the extraction of text from a reconstructed document                               | 3               | 25-11      | 27-11     |
| 5.2   | Prepare benchmarking scenarios for various input types                                       | 3               | 25-11      | 27-11     |
| 5.3   | Perform automated benchmarking of reconstruction algorithms using automated text extraction  | 3               | 27-11      | 29-11     |
| 5.4   | Perform manual benchmarking of reconstruction algorithms based on final document readability | 4               | 26-11      | 29-11     |
| 5.5   | Construct heuristics for algorithm selection                                                 | 2               | 29-11      | 30-11     |
| **6** | **Integration, UI**                                                                          | **34**          | **1-11**   | **4-12**  |
| 6.1   | Integrate modules into an unified pipeline                                                   | 4               | 1-12       | 4-12      |
| 6.2   | Building UI                                                                                  | 30              | 1-11       | 30-11     |
| **7** | **Documentation & Thesis writing**                                                           | **62**          | **1-12**   | **31-01** |
| 7.1   | Compile existing documentation and benchmarking results into initial thesis draft            | 20              | 1-12       | 20-12     |
| 7.2   | Write core chapters for thesis                                                               | 38              | 1-12       | 7-01      |
| 7.3   | Final buffer time, thesis polishing and defense presentation                                 | 25              | 7-01       | 31-01     |

### 7.2 RACI Matrix

| WBS   | Responsible | Accountable | Consulted | Informed |
|-------|-------------|-------------|-----------|----------|
| **1** |             |             |           |          |
| 1.1   | MS, HS, ZZ  | HS          | JR        | ---      |
| 1.2   | MS, HS, ZZ  | HS          | ---       | JR       |
| 1.3   | MS, HS      | HS          | ZZ        | JR       |
| 1.4   | ZZ          | ZZ          | MS, HS    | JR       |
| 1.5   | MS, ZZ      | ZZ          | HS        | JR       |
| 1.6   | HS, ZZ      | ZZ          | MS        | ---      |
| 1.7   | MS, HS      | MS          | ZZ        | ---      |
| 1.8   | MS, HS, ZZ  | MS          | ---       | ---      |
| 1.9   | MS          | MS          | HS, ZZ    | ---      |
| 1.10  | MS, HS, ZZ  | MS          | JR        | ---      |
| **2** |             |             |           |          |
| 2.1   | ZZ          | ZZ          | MS, HS    | ---      |
| 2.2   | MS, HS, ZZ  | HS          | ---       | ---      |
| 2.3   | MS          | MS          | HS, ZZ    | ---      |
| 2.4   | HS          | HS          | MS, ZZ    | ---      |
| 2.5   | ZZ          | ZZ          | MS, HS    | ---      |
| 2.6   | MS          | MS          | HS, ZZ    | ---      |
| 2.7   | HS          | HS          | MS, ZZ    | JR       |
| **3** |             |             |           |          |
| 3.1   | HS          | HS          | MS, ZZ    | ---      |
| 3.2   | MS          | MS          | HS, ZZ    | ---      |
| 3.3   | ZZ          | ZZ          | MS, HS    | ---      |
| **4** |             |             |           |          |
| 4.1   | MS, HS, ZZ  | HS          | ---       | JR       |
| 4.2   | MS, HS, ZZ  | MS          | ---       | JR       |
| 4.3   | ZZ          | ZZ          | MS, HS    | ---      |
| **5** |             |             |           |          |
| 5.1   | ZZ          | ZZ          | MS, HS    | ---      |
| 5.2   | HS          | HS          | MS, ZZ    | ---      |
| 5.3   | MS          | MS          | HS, ZZ    | ---      |
| 5.4   | MS, HS, ZZ  | ZZ          | ---       | ---      |
| 5.5   | HS          | HS          | MS, ZZ    | JR       |
| **6** |             |             |           |          |
| 6.1   | ZZ          | ZZ          | MS, HS    | JR       |
| 6.2   | MS, HS, ZZ  | MS          | HS, ZZ    | JR       |
| **7** |             |             |           |          |
| 7.1   | MS, HS, ZZ  | ZZ          | ---       | ---      |
| 7.2   | MS, HS, ZZ  | HS          | JR        | ---      |
| 7.3   | MS, HS, ZZ  | MS          | ---       | JR       |
|       |             |             |           |          |

## 8. Glossary

| Term                                      | Definition                                                                                                                                                                                    |
| :--------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| **APD (Archiwum Prac Dyplomowych)** | University Thesis Archive; official web portal of Warsaw University of Technology used for thesis submission, anti-plagiarism verification, and archiving.                                    |
| **MVP (Minimum Viable Product)**    | The minimal functional scope of the project fulfilling all foundational requirements for academic project evaluation and defense.                                                             |
| **Module 1**    | The document-splitting module, whose scope includes splitting an image into several fragments and arranging those fragments against a background.                                                              |
| **Module 2**    | The document reconstruction module, whose scope includes extracting individual fragments from an image and reconstructing the original document based on the fragments' shape and content.                                                              |



