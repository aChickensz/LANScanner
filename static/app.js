document.addEventListener("DOMContentLoaded", () => {
  const tableBody = document.querySelector("#devices-table tbody");
  const scanForm = document.getElementById("scan-form");
  const nameFilterInput = document.getElementById("filter-name");
  const subnetFilterInput = document.getElementById("filter-subnet");
  
  let devices = []; // Store all devices globally
  let currentSortField = "ip";
  let currentSortDir = "asc";

  // Fetch devices from server
  async function fetchDevices() {
    try {
      const res = await fetch("/devices");
      devices = await res.json();
      renderDevices();
      
      // Update last updated timestamp
      const lastUpdatedElement = document.getElementById("last-updated");
      if (lastUpdatedElement) {
        const now = new Date();
        lastUpdatedElement.textContent = now.toLocaleTimeString();
      }
    } catch (error) {
      console.error("Error fetching devices:", error);
    }
  }

  // Apply sorting to devices array
  function sortDevices(devicesToSort) {
    return [...devicesToSort].sort((a, b) => {
      const aVal = a[currentSortField] || "";
      const bVal = b[currentSortField] || "";
      
      // Handle numeric sorting for IP addresses
      if (currentSortField === "ip") {
        const aIP = aVal.split('.').map(num => parseInt(num, 10));
        const bIP = bVal.split('.').map(num => parseInt(num, 10));
        
        for (let i = 0; i < 4; i++) {
          if (aIP[i] !== bIP[i]) {
            return currentSortDir === "asc" ? aIP[i] - bIP[i] : bIP[i] - aIP[i];
          }
        }
        return 0;
      } 
      
      // String comparison for other fields
      if (currentSortDir === "asc") {
        return String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
      } else {
        return String(bVal).localeCompare(String(aVal), undefined, { numeric: true });
      }
    });
  }

  // Apply filters to devices array
  function applyFilters(devicesToFilter) {
    const nameFilter = nameFilterInput.value.toLowerCase().trim();
    const subnetFilter = subnetFilterInput.value.toLowerCase().trim();
    
    return devicesToFilter.filter(device => {
      const deviceName = (device.name || "").toLowerCase();
      const deviceSubnet = (device.subnet || "").toLowerCase();
      
      const nameMatch = !nameFilter || deviceName.includes(nameFilter);
      const subnetMatch = !subnetFilter || deviceSubnet.includes(subnetFilter);
      
      return nameMatch && subnetMatch;
    });
  }

  // Render the filtered and sorted devices to the table
  function renderDevices() {
    const filteredDevices = applyFilters(devices);
    const sortedDevices = sortDevices(filteredDevices);
    
    // Update device count badge
    const deviceCountElement = document.getElementById("device-count");
    if (deviceCountElement) {
      deviceCountElement.innerHTML = `
        <span class="badge bg-primary">${filteredDevices.length} of ${devices.length} devices</span>
      `;
    }
    
    tableBody.innerHTML = "";
    
    if (sortedDevices.length === 0) {
      const emptyRow = document.createElement("tr");
      emptyRow.innerHTML = `<td colspan="5" class="text-center">No devices found</td>`;
      tableBody.appendChild(emptyRow);
      return;
    }
    
    sortedDevices.forEach(device => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td data-label="IP">${device.ip || ""}</td>
        <td data-label="MAC">${device.mac || ""}</td>
        <td data-label="Name"><input class="form-control form-control-sm name-input" data-ip="${device.ip}" value="${device.name || ""}"></td>
        <td data-label="Subnet"><input class="form-control form-control-sm subnet-input" data-ip="${device.ip}" value="${device.subnet || ""}"></td>
        <td data-label="First Seen">${device.first_seen || ""}</td>
      `;
      tableBody.appendChild(row);
    });
    
    // Update sort indicators in header
    document.querySelectorAll(".sort-btn").forEach(btn => {
      const field = btn.dataset.field;
      if (field === currentSortField) {
        btn.textContent = `${btn.textContent.replace(" ▲", "").replace(" ▼", "")} ${currentSortDir === "asc" ? "▲" : "▼"}`;
      } else {
        btn.textContent = btn.textContent.replace(" ▲", "").replace(" ▼", "");
      }
    });
  }

  // Update device information on the server
  async function updateDevice(ip, field, value) {
    try {
      const response = await fetch("/devices/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip, [field]: value })
      });
      
      const result = await response.json();
      
      if (result.status === "ok") {
        // Update local device data
        const deviceIndex = devices.findIndex(d => d.ip === ip);
        if (deviceIndex !== -1) {
          devices[deviceIndex][field] = value;
        }
      } else {
        console.error("Error updating device:", result.message);
      }
    } catch (error) {
      console.error("Error updating device:", error);
    }
  }

  // Event listeners
  
  // Handle sort button clicks
  document.querySelectorAll(".sort-btn").forEach(button => {
    button.addEventListener("click", () => {
      const field = button.dataset.field;
      if (field === currentSortField) {
        currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
      } else {
        currentSortField = field;
        currentSortDir = "asc";
      }
      renderDevices();
    });
  });

  // Handle filter input changes
  nameFilterInput.addEventListener("input", () => {
    renderDevices();
  });
  
  subnetFilterInput.addEventListener("input", () => {
    renderDevices();
  });

  // Handle device name and subnet input changes
  tableBody.addEventListener("input", (e) => {
    const input = e.target;
    if (!input.classList.contains("name-input") && !input.classList.contains("subnet-input")) {
      return;
    }
    
    const ip = input.dataset.ip;
    if (!ip) return;
    
    if (input.classList.contains("name-input")) {
      updateDevice(ip, "name", input.value);
    } else if (input.classList.contains("subnet-input")) {
      updateDevice(ip, "subnet", input.value);
    }
  });

  // Handle scan form submission
  scanForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const subnet = document.getElementById("subnet-input").value.trim();
    if (!subnet) return;
    
    const scanButton = scanForm.querySelector("button");
    scanButton.disabled = true;
    scanButton.textContent = "Scanning...";
    
    try {
      await fetch("/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subnet })
      });
      
      // Wait 5 seconds before refreshing the device list
      setTimeout(() => {
        fetchDevices();
        scanButton.disabled = false;
        scanButton.textContent = "Scan Now";
      }, 5000);
    } catch (error) {
      console.error("Error triggering scan:", error);
      scanButton.disabled = false;
      scanButton.textContent = "Scan Now";
    }
  });

  // Initial fetch and set up auto-refresh
  fetchDevices();
  setInterval(fetchDevices, 60000); // Refresh every minute
});
