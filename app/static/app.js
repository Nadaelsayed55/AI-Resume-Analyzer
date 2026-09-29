let token = localStorage.getItem("token");
let lastResumeId = null;
let editingJobId = null;

const $ = id => document.getElementById(id);

function headers() {
    return token
        ? {"Authorization": "Bearer " + token}
        : {};
}

async function api(url, options = {}) {

    options.headers = {
        ...(options.headers || {}),
        ...headers()
    };

    const r = await fetch(url, options);

    const d = await r.json().catch(() => ({}));

    if (!r.ok) {
        throw new Error(d.detail || "Request failed");
    }

    return d;
}

function err(e) {
    alert(e.message);
}


/* =========================
   REGISTER
========================= */

$("register").onclick = async () => {

    try {

        let d = await api("/api/auth/register", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                name: $("name").value,
                email: $("email").value,
                password: $("password").value
            })
        });

        token = d.token;

        localStorage.setItem("token", token);

        $("authStatus").textContent =
            "Registered and logged in.";

    } catch (e) {
        err(e);
    }
};


/* =========================
   LOGIN
========================= */

$("login").onclick = async () => {

    try {

        let d = await api("/api/auth/login", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email: $("email").value,
                password: $("password").value
            })
        });

        token = d.token;

        localStorage.setItem("token", token);

        $("authStatus").textContent =
            "Logged in.";

    } catch (e) {
        err(e);
    }
};


/* =========================
   LOGOUT
========================= */

$("logout").onclick = () => {

    token = null;

    localStorage.removeItem("token");

    $("authStatus").textContent =
        "Logged out.";
};


/* =========================
   UPLOAD RESUME
========================= */

$("upload").onclick = async () => {

    try {

        let f = $("resumeFile").files[0];

        if (!f) {
            return alert("Choose a PDF or DOCX first.");
        }

        let form = new FormData();

        form.append("file", f);

        let d = await api("/api/resumes/upload", {
            method: "POST",
            body: form
        });

        lastResumeId = d.resume_id;

        $("analysis").textContent =
            JSON.stringify(d.analysis, null, 2);

        alert(
            "Resume uploaded and analyzed successfully!"
        );

        loadJobs();

    } catch (e) {
        err(e);
    }
};


/* =========================
   LOAD JOBS
========================= */

async function loadJobs() {

    try {

        let q = encodeURIComponent(
            $("jobQuery").value
        );

        let l = encodeURIComponent(
            $("jobLocation").value
        );

        let jobs = await api(
            `/api/jobs?q=${q}&location=${l}`
        );

        $("jobs").innerHTML = "";

        if (!jobs.length) {

            $("jobs").innerHTML =
                "<p>No jobs found.</p>";

            return;
        }


        jobs.forEach(j => {

            let div = document.createElement("div");

            div.className = "job";

            div.innerHTML = `

                <h3>${j.title}</h3>

                <p>
                    <strong>Company:</strong>
                    ${j.company}
                </p>

                <p>
                    <strong>Location:</strong>
                    ${j.location}
                </p>

                <p>
                    <strong>Description:</strong>
                    ${j.description}
                </p>

                <p>
                    <strong>Required Skills:</strong>
                    ${j.skills}
                </p>

                <button class="matchButton">
                    Match My Resume
                </button>

                <button class="editButton">
                    Edit Job
                </button>

                <button class="deleteButton">
                    Delete Job
                </button>

                <div class="matchResult"></div>

            `;


            /* =========================
               MATCH RESUME
            ========================= */

            let matchButton =
                div.querySelector(".matchButton");

            let result =
                div.querySelector(".matchResult");


            matchButton.onclick = async () => {

                try {

                    if (!lastResumeId) {

                        return alert(
                            "Please upload and analyze your resume first."
                        );

                    }

                    matchButton.disabled = true;

                    matchButton.textContent =
                        "Analyzing...";


                    let m = await api(
                        `/api/match/${lastResumeId}/${j.id}`,
                        {
                            method: "POST"
                        }
                    );


                    result.innerHTML = `

                        <div class="match-box">

                            <h4>
                                Job Match Result
                            </h4>

                            <p>
                                <strong>Match Score:</strong>
                                ${m.score}%
                            </p>

                            <p>
                                <strong>Matched Skills:</strong>
                                ${m.matched_skills.join(", ") || "None"}
                            </p>

                            <p>
                                <strong>Missing Skills:</strong>
                                ${m.missing_skills.join(", ") || "None"}
                            </p>

                            <p>
                                <strong>Explanation:</strong>
                                ${m.explanation}
                            </p>

                        </div>

                    `;


                } catch (e) {

                    err(e);

                } finally {

                    matchButton.disabled = false;

                    matchButton.textContent =
                        "Match My Resume";

                }

            };


            /* =========================
               EDIT JOB
            ========================= */

            let editButton =
                div.querySelector(".editButton");


            editButton.onclick = () => {

                editingJobId = j.id;

                $("jt").value =
                    j.title;

                $("jc").value =
                    j.company;

                $("jl").value =
                    j.location;

                $("js").value =
                    j.skills;

                $("jd").value =
                    j.description;


                $("addJob").textContent =
                    "Update Job";


                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: "smooth"
                });

            };


            /* =========================
               DELETE JOB
            ========================= */

            let deleteButton =
                div.querySelector(".deleteButton");


            deleteButton.onclick = async () => {

                let confirmed = confirm(
                    `Are you sure you want to delete "${j.title}"?`
                );

                if (!confirmed) {
                    return;
                }


                try {

                    deleteButton.disabled = true;

                    deleteButton.textContent =
                        "Deleting...";


                    await api(
                        `/api/jobs/${j.id}`,
                        {
                            method: "DELETE"
                        }
                    );


                    alert(
                        "Job deleted successfully."
                    );


                    loadJobs();


                } catch (e) {

                    deleteButton.disabled = false;

                    deleteButton.textContent =
                        "Delete Job";

                    err(e);

                }

            };


            $("jobs").appendChild(div);

        });

    } catch (e) {

        err(e);

    }
}


/* =========================
   SEARCH JOBS
========================= */

$("searchJobs").onclick = loadJobs;


/* =========================
   ADD / UPDATE JOB
========================= */

$("addJob").onclick = async () => {

    try {

        const jobData = {

            title: $("jt").value,

            company: $("jc").value,

            location: $("jl").value,

            skills: $("js").value,

            description: $("jd").value

        };


        /* =========================
           UPDATE EXISTING JOB
        ========================= */

        if (editingJobId) {

            await api(
                `/api/jobs/${editingJobId}`,
                {
                    method: "PUT",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(jobData)
                }
            );


            alert(
                "Job updated successfully."
            );


            editingJobId = null;

            $("addJob").textContent =
                "Add Job";


        }

        /* =========================
           ADD NEW JOB
        ========================= */

        else {

            await api(
                "/api/jobs",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(jobData)
                }
            );


            alert(
                "Job added successfully."
            );

        }


        /* Clear fields */

        $("jt").value = "";
        $("jc").value = "";
        $("jl").value = "";
        $("js").value = "";
        $("jd").value = "";


        loadJobs();


    } catch (e) {

        err(e);

    }
};


/* =========================
   CAREER ADVICE
========================= */

$("advice").onclick = async () => {

    try {

        if (!lastResumeId) {

            return alert(
                "Please upload a resume first."
            );

        }

        let d = await api(
            `/api/career-advice/${lastResumeId}`
        );

        $("adviceBox").textContent =
            d.advice;

    } catch (e) {

        err(e);

    }
};


/* =========================
   INITIAL LOAD
========================= */

loadJobs();