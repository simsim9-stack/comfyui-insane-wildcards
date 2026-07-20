import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ---------------------------------------------------------------------------
// Wildcard list loader
// ---------------------------------------------------------------------------
let wildcards_list = [];
let wildcard_status = "loading...";

async function load_wildcards() {
	try {
		let res = await api.fetchApi("/insanewildcards/wildcards/list");
		let data = await res.json();
		wildcards_list = data.data;
		wildcard_status = `🟢 ${data.count} wildcards`;
	} catch (error) {
		console.error("[InsaneWildcards] Failed to load wildcards:", error);
		wildcard_status = "⚠️ error";
	}
}

load_wildcards();

// ---------------------------------------------------------------------------
// Extension registration
// ---------------------------------------------------------------------------
app.registerExtension({
	name: "InsaneWildcards",

	nodeCreated(node, app) {
		if (node.comfyClass !== "InsaneWildcards") return;

		// Find widgets by name (robust against index changes)
		const textbox = node.widgets.find((w) => w.name === "wildcard_text");
		const selector = node.widgets.find((w) => w.name === "Select to add Wildcard");

		if (!textbox || !selector) return;

		// ---- callback: append selected wildcard to text box ----
		selector.callback = async function (value, canvas, n, pos, e) {
			if (!n || !n._wildcard_value) return;
			if (textbox.value !== "") textbox.value += ", ";
			textbox.value += n._wildcard_value;

			// Refresh wildcard status in on-demand mode
			await load_wildcards();
			app.canvas.setDirty(true);
		};

		// ---- override value: getter shows label, setter stores selection ----
		Object.defineProperty(selector, "value", {
			set(value) {
				if (
					value !== "Select the Wildcard to add to the text" &&
					!value.startsWith("🟢") &&
					!value.startsWith("⚠️")
				) {
					node._wildcard_value = value;
				}
			},
			get() {
				return `Select Wildcard ${wildcard_status}`;
			},
			configurable: true,
		});

		// ---- override options to be dynamic (updated via API) ----
		Object.defineProperty(selector.options, "values", {
			set() {},
			get() {
				return wildcards_list;
			},
			configurable: true,
		});

		// ---- prevent the label from being serialized into the workflow ----
		selector.serializeValue = () => "Select the Wildcard to add to the text";
	},
});
