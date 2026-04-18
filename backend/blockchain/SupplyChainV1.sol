// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ZF ChainMind Supply Chain Finance v1.0
 * @author ZF Logistics Intelligence Team
 * @notice This contract automates carbon-aware payments and records immutable audit logs.
 */
contract SupplyChainV1 {
    address public owner;
    
    struct Shipment {
        string routeId;
        address carrier;
        uint256 co2Threshold; // in grams
        uint256 value_wei;
        uint256 timestamp;
        bool isVerified;
        bool isPaid;
    }

    mapping(string => Shipment) public shipments;
    event ShipmentLogged(string indexed routeId, uint256 co2Threshold, uint256 value);
    event PaymentExecuted(string indexed routeId, address indexed carrier, uint256 amount);
    event CarbonAuditFailed(string indexed routeId, uint256 actualCo2);

    modifier onlyOwner() {
        require(msg.sender == owner, "Direct access prohibited");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Registers a new shipment with a carbon threshold.
     */
    function recordShipment(
        string memory _id, 
        address _carrier, 
        uint256 _co2Threshold, 
        uint256 _value
    ) external onlyOwner {
        shipments[_id] = Shipment(_id, _carrier, _co2Threshold, _value, block.timestamp, false, false);
        emit ShipmentLogged(_id, _co2Threshold, _value);
    }

    /**
     * @notice Checks carbon compliance and executes payment.
     * @dev In a real deployment, '_actualCo2' would be provided by a Chainlink Oracle.
     */
    function verifyAndPay(string memory _id, uint256 _actualCo2) external onlyOwner {
        Shipment storage s = shipments[_id];
        require(s.carrier != address(0), "Shipment not found");
        require(!s.isPaid, "Already settled");

        if (_actualCo2 <= s.co2Threshold) {
            s.isVerified = true;
            s.isPaid = true;
            
            // Payment logic mock (would use address(s.carrier).transfer(s.value_wei))
            emit PaymentExecuted(_id, s.carrier, s.value_wei);
        } else {
            emit CarbonAuditFailed(_id, _actualCo2);
        }
    }
}
