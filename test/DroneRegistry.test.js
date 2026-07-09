const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("DroneRegistry", function () {
  let registry;
  let owner;
  let operator;
  let other;

  beforeEach(async function () {
    [owner, operator, other] = await ethers.getSigners();
    const DroneRegistry = await ethers.getContractFactory("DroneRegistry");
    registry = await DroneRegistry.deploy();
  });

  // ─── Registration ──────────────────────────────────────────────────────

  describe("registerDrone", function () {
    it("should allow owner to register a drone", async function () {
      await registry.registerDrone("DMT-001", operator.address);
      const drone = await registry.drones("DMT-001");
      expect(drone.droneId).to.equal("DMT-001");
      expect(drone.owner).to.equal(operator.address);
      expect(drone.isActive).to.equal(true);
    });

    it("should emit DroneRegistered event", async function () {
      await expect(registry.registerDrone("DMT-001", operator.address))
        .to.emit(registry, "DroneRegistered")
        .withArgs("DMT-001", operator.address, await getBlockTimestamp());
    });

    it("should revert if non-owner tries to register", async function () {
      await expect(
        registry.connect(other).registerDrone("DMT-002", operator.address)
      ).to.be.revertedWithCustomError(registry, "OwnableUnauthorizedAccount");
    });

    it("should revert on duplicate droneId", async function () {
      await registry.registerDrone("DMT-001", operator.address);
      await expect(
        registry.registerDrone("DMT-001", operator.address)
      ).to.be.revertedWith("DroneRegistry: already registered");
    });

    it("should revert on empty droneId", async function () {
      await expect(
        registry.registerDrone("", operator.address)
      ).to.be.revertedWith("DroneRegistry: empty droneId");
    });

    it("should revert on zero address operator", async function () {
      await expect(
        registry.registerDrone("DMT-001", ethers.ZeroAddress)
      ).to.be.revertedWith("DroneRegistry: zero address");
    });
  });

  // ─── Passage Logging ───────────────────────────────────────────────────

  describe("logPassage", function () {
    beforeEach(async function () {
      await registry.registerDrone("DMT-001", operator.address);
    });

    it("should log a passage entry", async function () {
      await registry.logPassage("DMT-001", "NODE-A1", 12971599, 77594566);
      const logs = await registry.getPassageLogs("DMT-001");
      expect(logs.length).to.equal(1);
      expect(logs[0].nodeId).to.equal("NODE-A1");
      expect(logs[0].lat).to.equal(12971599);
      expect(logs[0].lon).to.equal(77594566);
    });

    it("should emit PassageLogged event", async function () {
      await expect(registry.logPassage("DMT-001", "NODE-A1", 12971599, 77594566))
        .to.emit(registry, "PassageLogged")
        .withArgs("DMT-001", "NODE-A1", 12971599, 77594566, await getBlockTimestamp());
    });

    it("should accumulate multiple passage logs", async function () {
      await registry.logPassage("DMT-001", "NODE-A1", 12971599, 77594566);
      await registry.logPassage("DMT-001", "NODE-B2", 13005000, 77610000);
      const logs = await registry.getPassageLogs("DMT-001");
      expect(logs.length).to.equal(2);
    });

    it("should revert for unregistered drone", async function () {
      await expect(
        registry.logPassage("DMT-999", "NODE-A1", 12971599, 77594566)
      ).to.be.revertedWith("DroneRegistry: drone not registered");
    });

    it("should revert if drone is inactive", async function () {
      await registry.setDroneStatus("DMT-001", false);
      await expect(
        registry.logPassage("DMT-001", "NODE-A1", 12971599, 77594566)
      ).to.be.revertedWith("DroneRegistry: drone is not active");
    });
  });

  // ─── Status Management ─────────────────────────────────────────────────

  describe("setDroneStatus", function () {
    beforeEach(async function () {
      await registry.registerDrone("DMT-001", operator.address);
    });

    it("should deactivate a drone", async function () {
      await registry.setDroneStatus("DMT-001", false);
      const drone = await registry.drones("DMT-001");
      expect(drone.isActive).to.equal(false);
    });

    it("should reactivate a drone", async function () {
      await registry.setDroneStatus("DMT-001", false);
      await registry.setDroneStatus("DMT-001", true);
      const drone = await registry.drones("DMT-001");
      expect(drone.isActive).to.equal(true);
    });

    it("should emit DroneStatusUpdated event", async function () {
      await expect(registry.setDroneStatus("DMT-001", false))
        .to.emit(registry, "DroneStatusUpdated")
        .withArgs("DMT-001", false);
    });

    it("should revert if non-owner tries to update status", async function () {
      await expect(
        registry.connect(other).setDroneStatus("DMT-001", false)
      ).to.be.revertedWithCustomError(registry, "OwnableUnauthorizedAccount");
    });
  });

  // ─── Helpers ────────────────────────────────────────────────────────────

  describe("helpers", function () {
    it("getDroneCount should return correct count", async function () {
      expect(await registry.getDroneCount()).to.equal(0);
      await registry.registerDrone("DMT-001", operator.address);
      await registry.registerDrone("DMT-002", operator.address);
      expect(await registry.getDroneCount()).to.equal(2);
    });
  });
});

// Returns the timestamp of the next block (used for event matching)
async function getBlockTimestamp() {
  const block = await ethers.provider.getBlock("latest");
  return block.timestamp + 1;
}
