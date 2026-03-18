import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

/*
 * ContactSheet v2 — Visual Grid Picker
 *
 * Button on PreprocessorContactSheet nodes:
 *  🎯 Pick from Grid — visual picker with real thumbnails from last run
 *  Click a thumbnail → injects the corresponding preprocessor workflow
 *  into the canvas
 */

app.registerExtension({
    name: "ContactSheet.WorkflowInject",

    async nodeCreated(node) {
        if (node.comfyClass !== "PreprocessorContactSheet") return;

        node.addWidget(
            "button",
            "\u{1F3AF} Pick from Grid",
            null,
            async () => {
                try {
                    await openGridPicker(node);
                } catch (e) {
                    console.error("[ContactSheet]", e);
                    alert("ContactSheet error: " + e.message);
                }
            }
        );
    },
});


/* ================================================================== */
/*  GRID PICKER — visual thumbnails → inject workflow                  */
/* ================================================================== */

async function openGridPicker(node) {
    const nodeId = node.id;

    const resp = await api.fetchApi(
        `/contact_sheet/cells?node_id=${encodeURIComponent(nodeId)}`
    );
    const data = await resp.json();

    if (!data.cells || data.cells.length === 0) {
        alert(
            "No preprocessor results cached yet.\n" +
            "Run the workflow first (Queue Prompt), then use this picker."
        );
        return;
    }

    // Filter out the ORIGINAL cell — no workflow to inject for it
    const cells = data.cells.filter((c) => c.aio !== "__original__");

    if (cells.length === 0) {
        alert("No preprocessor results to show (only original image found).");
        return;
    }

    // --- Overlay ---
    const overlay = el("div", {
        position: "fixed", top: "0", left: "0", width: "100%", height: "100%",
        background: "rgba(0,0,0,0.7)", zIndex: "10000",
        display: "flex", alignItems: "center", justifyContent: "center",
    });
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) overlay.remove();
    });

    // --- Panel ---
    const panel = el("div", {
        background: "#1e1e2e", borderRadius: "14px", padding: "24px",
        maxWidth: "92vw", maxHeight: "88vh", overflowY: "auto",
        color: "#cdd6f4", fontFamily: "sans-serif",
        boxShadow: "0 12px 48px rgba(0,0,0,0.7)",
    });

    // Title
    panel.appendChild(
        el("h2", { margin: "0 0 6px", color: "#a6e3a1", fontSize: "20px" },
           "\u{1F3AF} Pick a Preprocessor from Grid")
    );
    panel.appendChild(
        el("p", { margin: "0 0 16px", fontSize: "13px", color: "#6c7086" },
           "Click a thumbnail to inject its workflow into the canvas. " +
           "These are the actual results from the last run.")
    );

    // Search
    const search = document.createElement("input");
    Object.assign(search.style, {
        width: "100%", padding: "10px 14px", marginBottom: "16px",
        background: "#313244", border: "1px solid #45475a",
        borderRadius: "8px", color: "#cdd6f4", fontSize: "14px",
        outline: "none", boxSizing: "border-box",
    });
    search.placeholder = "Search preprocessors...";
    panel.appendChild(search);

    const catColor = {
        segment: "#cba6f7", edge: "#89b4fa", lineart: "#74c7ec",
        pose: "#f38ba8", depth: "#a6e3a1", normal: "#f9e2af",
        face: "#f5c2e7", color: "#fab387", tile: "#9399b2",
        flow: "#94e2d5",
    };

    // Grid
    const grid = el("div", {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
        gap: "12px",
    });

    function renderGrid(filter = "") {
        grid.innerHTML = "";
        const lf = filter.toLowerCase();

        // Group by category
        const grouped = {};
        for (const cell of cells) {
            if (lf && !cell.name.toLowerCase().includes(lf) &&
                !cell.aio.toLowerCase().includes(lf) &&
                !cell.cat.toLowerCase().includes(lf)) {
                continue;
            }
            (grouped[cell.cat] ||= []).push(cell);
        }

        for (const [cat, items] of Object.entries(grouped)) {
            // Category header spanning full width
            const catHeader = el("div", {
                gridColumn: "1 / -1",
                fontSize: "11px", fontWeight: "700",
                textTransform: "uppercase",
                color: catColor[cat] || "#9399b2",
                margin: "8px 0 0", letterSpacing: "1.2px",
                borderBottom: `1px solid ${catColor[cat] || "#9399b2"}33`,
                paddingBottom: "4px",
            }, CATEGORY_LABELS_JS[cat] || cat.toUpperCase());
            grid.appendChild(catHeader);

            for (const cell of items) {
                const card = el("div", {
                    borderRadius: "10px",
                    overflow: "hidden",
                    cursor: "pointer",
                    border: "2px solid #45475a",
                    background: "#313244",
                    transition: "all 0.15s ease",
                    position: "relative",
                });

                // Thumbnail image
                const img = document.createElement("img");
                img.src = `data:image/jpeg;base64,${cell.thumb}`;
                img.alt = cell.name;
                Object.assign(img.style, {
                    width: "100%", height: "auto", display: "block",
                });
                card.appendChild(img);

                // Label
                const label = el("div", {
                    padding: "8px 10px",
                    background: "rgba(0,0,0,0.4)",
                });

                label.appendChild(
                    el("div", {
                        fontSize: "13px", fontWeight: "700",
                        color: "#cdd6f4", marginBottom: "2px",
                    }, cell.name)
                );
                label.appendChild(
                    el("div", {
                        fontSize: "10px", fontWeight: "600",
                        textTransform: "uppercase", letterSpacing: "0.8px",
                        color: catColor[cell.cat] || "#9399b2",
                    }, cell.cat)
                );
                label.appendChild(
                    el("div", {
                        fontSize: "9px", color: "#585b70",
                        marginTop: "2px",
                    }, cell.aio)
                );

                card.appendChild(label);

                // Hover
                card.addEventListener("mouseenter", () => {
                    card.style.border = "2px solid #89b4fa";
                    card.style.transform = "scale(1.03)";
                    card.style.boxShadow = "0 4px 16px rgba(137,180,250,0.3)";
                });
                card.addEventListener("mouseleave", () => {
                    card.style.border = "2px solid #45475a";
                    card.style.transform = "scale(1)";
                    card.style.boxShadow = "none";
                });

                // Click → show AIO vs Dedicated choice
                card.addEventListener("click", () => {
                    showModeChoice(cell, overlay);
                });

                grid.appendChild(card);
            }
        }

        if (grid.children.length === 0) {
            grid.appendChild(
                el("div", {
                    gridColumn: "1 / -1", textAlign: "center",
                    color: "#6c7086", padding: "40px",
                    fontSize: "14px",
                }, "No preprocessors match your search.")
            );
        }
    }

    renderGrid();
    search.addEventListener("input", () => renderGrid(search.value));
    panel.appendChild(grid);

    // Close
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "Close";
    Object.assign(closeBtn.style, {
        marginTop: "16px", padding: "8px 28px", background: "#45475a",
        color: "#cdd6f4", border: "none", borderRadius: "6px",
        cursor: "pointer", fontSize: "14px", float: "right",
    });
    closeBtn.addEventListener("click", () => overlay.remove());
    panel.appendChild(closeBtn);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    requestAnimationFrame(() => search.focus());
}


// Category labels for JS side
const CATEGORY_LABELS_JS = {
    segment: "SEGMENTATION",
    edge: "EDGE DETECTION",
    lineart: "LINEART",
    pose: "POSE ESTIMATION",
    depth: "DEPTH",
    normal: "NORMAL MAP",
    face: "FACE",
    color: "COLOR / LUMINANCE",
    tile: "TILE / SHUFFLE",
    flow: "OPTICAL FLOW",
};


/* ================================================================== */
/*  Mode choice: AIO vs Dedicated node                                 */
/* ================================================================== */

function showModeChoice(cell, gridOverlay) {
    // Small popup over the grid overlay
    const popup = el("div", {
        position: "fixed", top: "0", left: "0", width: "100%", height: "100%",
        background: "rgba(0,0,0,0.5)", zIndex: "10002",
        display: "flex", alignItems: "center", justifyContent: "center",
    });
    popup.addEventListener("click", (e) => {
        if (e.target === popup) popup.remove();
    });

    const box = el("div", {
        background: "#1e1e2e", borderRadius: "14px", padding: "28px",
        minWidth: "400px", maxWidth: "500px",
        color: "#cdd6f4", fontFamily: "sans-serif",
        boxShadow: "0 12px 48px rgba(0,0,0,0.7)",
        textAlign: "center",
    });

    // Thumbnail preview
    const thumb = document.createElement("img");
    thumb.src = `data:image/jpeg;base64,${cell.thumb}`;
    Object.assign(thumb.style, {
        width: "160px", height: "auto", borderRadius: "8px",
        marginBottom: "16px", border: "2px solid #45475a",
    });
    box.appendChild(thumb);

    box.appendChild(
        el("h3", { margin: "0 0 4px", color: "#cdd6f4", fontSize: "18px" },
           cell.name)
    );
    box.appendChild(
        el("p", { margin: "0 0 20px", fontSize: "12px", color: "#6c7086" },
           "How do you want to import this preprocessor?")
    );

    // --- AIO Button ---
    const aioBtn = el("div", {
        padding: "14px 20px", margin: "8px 0",
        borderRadius: "10px", background: "#313244",
        cursor: "pointer", border: "2px solid #3f5e9e",
        transition: "all 0.12s", textAlign: "left",
    });
    aioBtn.addEventListener("mouseenter", () => {
        aioBtn.style.background = "#3f5e9e";
        aioBtn.style.borderColor = "#89b4fa";
    });
    aioBtn.addEventListener("mouseleave", () => {
        aioBtn.style.background = "#313244";
        aioBtn.style.borderColor = "#3f5e9e";
    });

    aioBtn.appendChild(
        el("div", { fontSize: "15px", fontWeight: "700", color: "#89b4fa",
                    marginBottom: "4px" },
           "\u{1F4E6} AIO Preprocessor")
    );
    aioBtn.appendChild(
        el("div", { fontSize: "12px", color: "#9399b2" },
           "Generic node with dropdown — fast, compact, no specific parameters exposed")
    );

    aioBtn.addEventListener("click", () => {
        popup.remove();
        gridOverlay.remove();
        enterPlacementMode(cell.aio, cell.name, "aio");
    });
    box.appendChild(aioBtn);

    // --- Dedicated Button ---
    const dedBtn = el("div", {
        padding: "14px 20px", margin: "8px 0",
        borderRadius: "10px", background: "#313244",
        cursor: "pointer", border: "2px solid #7c3f9e",
        transition: "all 0.12s", textAlign: "left",
    });
    dedBtn.addEventListener("mouseenter", () => {
        dedBtn.style.background = "#7c3f9e";
        dedBtn.style.borderColor = "#cba6f7";
    });
    dedBtn.addEventListener("mouseleave", () => {
        dedBtn.style.background = "#313244";
        dedBtn.style.borderColor = "#7c3f9e";
    });

    const nodeType = cell.node || cell.aio;
    dedBtn.appendChild(
        el("div", { fontSize: "15px", fontWeight: "700", color: "#cba6f7",
                    marginBottom: "4px" },
           `\u{1F3AF} ${nodeType}`)
    );
    dedBtn.appendChild(
        el("div", { fontSize: "12px", color: "#9399b2" },
           "Dedicated node with all parameters — thresholds, models, options for maximum control")
    );

    dedBtn.addEventListener("click", () => {
        popup.remove();
        gridOverlay.remove();
        enterPlacementMode(cell.aio, cell.name, "dedicated");
    });
    box.appendChild(dedBtn);

    // --- Both Button ---
    const bothBtn = el("div", {
        padding: "14px 20px", margin: "8px 0",
        borderRadius: "10px", background: "#313244",
        cursor: "pointer", border: "2px solid #45875a",
        transition: "all 0.12s", textAlign: "left",
    });
    bothBtn.addEventListener("mouseenter", () => {
        bothBtn.style.background = "#45875a";
        bothBtn.style.borderColor = "#a6e3a1";
    });
    bothBtn.addEventListener("mouseleave", () => {
        bothBtn.style.background = "#313244";
        bothBtn.style.borderColor = "#45875a";
    });

    bothBtn.appendChild(
        el("div", { fontSize: "15px", fontWeight: "700", color: "#a6e3a1",
                    marginBottom: "4px" },
           "\u{1F4E6}\u{1F3AF} Both (AIO + Dedicated)")
    );
    bothBtn.appendChild(
        el("div", { fontSize: "12px", color: "#9399b2" },
           "Place both workflows side by side — click once, they'll be stacked vertically")
    );

    bothBtn.addEventListener("click", () => {
        popup.remove();
        gridOverlay.remove();
        enterPlacementMode(cell.aio, cell.name, "both");
    });
    box.appendChild(bothBtn);

    // Cancel
    const cancelBtn = document.createElement("button");
    cancelBtn.textContent = "Cancel";
    Object.assign(cancelBtn.style, {
        marginTop: "14px", padding: "6px 24px", background: "#45475a",
        color: "#9399b2", border: "none", borderRadius: "6px",
        cursor: "pointer", fontSize: "13px",
    });
    cancelBtn.addEventListener("click", () => popup.remove());
    box.appendChild(cancelBtn);

    popup.appendChild(box);
    document.body.appendChild(popup);
}


function showToast(text) {
    const toast = el("div", {
        position: "fixed", bottom: "30px", left: "50%",
        transform: "translateX(-50%)",
        background: "#a6e3a1", color: "#1e1e2e",
        padding: "12px 28px", borderRadius: "10px",
        fontSize: "15px", fontWeight: "700",
        boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        zIndex: "10003",
        transition: "opacity 0.4s ease",
    }, text);
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 400);
    }, 2500);
}


/* ================================================================== */
/*  Placement mode: click on canvas to place the workflow              */
/* ================================================================== */

function enterPlacementMode(aioName, displayName, mode) {
    const lgCanvas = app.canvas;

    // Banner
    const modeLabel = mode === "aio" ? "AIO" : mode === "dedicated" ? "Dedicated" : "AIO + Dedicated";
    const bannerBg = mode === "aio"
        ? "linear-gradient(135deg, #3f5e9e, #2d4373)"
        : mode === "dedicated"
            ? "linear-gradient(135deg, #7c3f9e, #5a2d73)"
            : "linear-gradient(135deg, #45875a, #2d5e3a)";

    const banner = el("div", {
        position: "fixed", top: "0", left: "0", width: "100%",
        padding: "14px 0", textAlign: "center",
        background: bannerBg,
        color: "#fff", fontSize: "15px", fontWeight: "700",
        fontFamily: "sans-serif",
        zIndex: "10001",
        boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        transition: "opacity 0.3s ease",
        pointerEvents: "none",
    });
    banner.innerHTML =
        `<span style="margin-right:12px">\u{1F4CC}</span>` +
        `Click on canvas to place <b>${displayName}</b> (${modeLabel})` +
        `<span style="margin-left:16px;font-size:12px;opacity:0.7">ESC to cancel</span>`;
    document.body.appendChild(banner);

    // Transparent overlay to capture click without interfering with LiteGraph
    const clickOverlay = el("div", {
        position: "fixed", top: "0", left: "0", width: "100%", height: "100%",
        zIndex: "10000",
        cursor: "crosshair",
        background: "transparent",
    });

    function screenToGraph(clientX, clientY) {
        // Get the canvas DOM element
        const canvasEl = lgCanvas.canvas;
        const rect = canvasEl.getBoundingClientRect();

        // Mouse position relative to the canvas element
        const mx = clientX - rect.left;
        const my = clientY - rect.top;

        // LiteGraph stores offset (pan) and scale (zoom)
        const offset = lgCanvas.ds?.offset || [0, 0];
        const scale = lgCanvas.ds?.scale || 1;

        // Convert: graph_pos = (mouse_pos / scale) - offset
        const gx = (mx / scale) - offset[0];
        const gy = (my / scale) - offset[1];
        return [gx, gy];
    }

    function onClick(e) {
        e.preventDefault();
        e.stopPropagation();
        const [gx, gy] = screenToGraph(e.clientX, e.clientY);
        cleanup();
        injectWorkflowAt(aioName, mode, gx, gy);
        showToast(`\u2713 ${displayName} (${modeLabel}) placed!`);
    }

    function onKeyDown(e) {
        if (e.key === "Escape") {
            cleanup();
            showToast("\u2718 Placement cancelled");
        }
    }

    function cleanup() {
        clickOverlay.removeEventListener("click", onClick);
        document.removeEventListener("keydown", onKeyDown, true);
        clickOverlay.remove();
        banner.style.opacity = "0";
        setTimeout(() => banner.remove(), 300);
    }

    clickOverlay.addEventListener("click", onClick);
    document.addEventListener("keydown", onKeyDown, true);
    document.body.appendChild(clickOverlay);
}


/* ================================================================== */
/*  Inject workflow at specific canvas coordinates                     */
/* ================================================================== */

async function injectWorkflowAt(preprocessorAio, mode, placeX, placeY) {
    if (mode === "both") {
        // Place AIO first, then Dedicated below it
        await placeOneWorkflow(preprocessorAio, "aio", placeX, placeY);
        await placeOneWorkflow(preprocessorAio, "dedicated", placeX, placeY + 500);
        return;
    }
    await placeOneWorkflow(preprocessorAio, mode, placeX, placeY);
}


async function placeOneWorkflow(preprocessorAio, mode, baseX, baseY) {
    const resp = await api.fetchApi(
        `/contact_sheet/workflow?preprocessor=${encodeURIComponent(preprocessorAio)}&mode=${mode}`
    );
    const wf = await resp.json();
    const graph = app.graph;

    const created = {};
    for (const nd of wf.nodes) {
        const newNode = LiteGraph.createNode(nd.type);
        if (!newNode) {
            console.warn(`[ContactSheet] Node type '${nd.type}' not found`);
            continue;
        }
        newNode.pos = [
            baseX + (nd.pos?.[0] || 0),
            baseY + (nd.pos?.[1] || 0),
        ];
        if (nd.size) {
            newNode.size = [...nd.size];
        }

        if (nd.widgets_values && newNode.widgets) {
            for (let i = 0; i < nd.widgets_values.length && i < newNode.widgets.length; i++) {
                newNode.widgets[i].value = nd.widgets_values[i];
            }
        }

        graph.add(newNode);
        created[nd.id] = newNode;
    }

    for (const link of wf.links) {
        const from = created[link[1]];
        const to = created[link[3]];
        if (!from || !to) continue;
        try {
            from.connect(link[2], to, link[4]);
        } catch (e) {
            console.warn("[ContactSheet] Link error:", e);
        }
    }

    // Create groups — set position AFTER adding to graph to avoid LiteGraph reset
    if (wf.groups?.length) {
        for (const g of wf.groups) {
            const group = new LiteGraph.LGraphGroup();
            group.title = g.title || "Workflow";
            group.color = g.color || "#3f5e9e";
            group.font_size = g.font_size || 24;

            const gx = baseX + (g.bounding?.[0] || 0);
            const gy = baseY + (g.bounding?.[1] || 0);
            const gw = g.bounding?.[2] || 1200;
            const gh = g.bounding?.[3] || 500;

            // Set bounding BEFORE add
            group._bounding = [gx, gy, gw, gh];
            group._pos = [gx, gy];
            group._size = [gw, gh];

            graph.add(group);

            // Force bounding AFTER add (LiteGraph may reset on add)
            group._bounding[0] = gx;
            group._bounding[1] = gy;
            group._bounding[2] = gw;
            group._bounding[3] = gh;
            if (group._pos) {
                group._pos[0] = gx;
                group._pos[1] = gy;
            }
            if (group._size) {
                group._size[0] = gw;
                group._size[1] = gh;
            }
        }
    }

    // Force canvas redraw with a small delay to let groups settle
    graph.setDirtyCanvas(true, true);
    setTimeout(() => {
        graph.setDirtyCanvas(true, true);
        if (app.canvas) app.canvas.draw(true, true);
    }, 50);
    console.log(`[ContactSheet] Placed ${preprocessorAio} (${mode}) at ${baseX}, ${baseY}`);
}


/* ================================================================== */
/*  Tiny helper                                                        */
/* ================================================================== */

function el(tag, style, text) {
    const e = document.createElement(tag);
    if (style && typeof style === "object") Object.assign(e.style, style);
    if (text) e.textContent = text;
    return e;
}
