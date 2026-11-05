pragma solidity ^0.8.20;

contract BirdSubscription {
    address public owner;
    uint256 public price;
    uint256 public constant SUBSCRIPTION_DURATION = 3 days;

    mapping(address => uint256) public subscriptionExpiry;

    event SubscriptionPurchased(
        address indexed user,
        uint256 expiry
    );

    constructor(uint256 _price) {
        owner = msg.sender;
        price = _price;
    }

    function subscribe() external payable {
        require(msg.value == price, "Incorrect paiment amount");

        uint256 startTime = block.timestamp;

        if (subscriptionExpiry[msg.sender] > startTime) {
            startTime = subscriptionExpiry[msg.sender];
        }

        subscriptionExpiry[msg.sender] =
            startTime + SUBSCRIPTION_DURATION;

        emit SubscriptionPurchased(
            msg.sender,
            subscriptionExpiry[msg.sender]
        );
    }

    function isSubscriptionActive(address user)
        external
        view
        returns (bool)
    {
        return subscriptionExpiry[user] > block.timestamp;
    }

    function withdraw() external {
        require(msg.sender == owner, "Only owner");

        uint256 balance = address(this).balance;

        require(balance > 0, "No funds");

        (bool success, ) = payable(owner).call{value: balance}("");

        require(success, "Transfer failed");
    }
}
