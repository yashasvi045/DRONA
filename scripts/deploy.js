const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying DroneRegistry with account:", deployer.address);

  const DroneRegistry = await ethers.getContractFactory("DroneRegistry");
  const registry = await DroneRegistry.deploy();
  await registry.waitForDeployment();

  console.log("DroneRegistry deployed to:", await registry.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
