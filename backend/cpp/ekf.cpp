#include "ekf.hpp"
#include <iostream>

using namespace Eigen;

EKF::EKF(double dt)
    : dt_(dt), state_dim_(5), meas_dim_(2)
{
    // State: [x, y, vx, vy, yaw]^T
    F_ = MatrixXd::Identity(state_dim_, state_dim_);
    F_(0, 2) = dt_;
    F_(1, 3) = dt_;

    // Measure positions only: z = [x, y]
    H_ = MatrixXd::Zero(meas_dim_, state_dim_);
    H_(0, 0) = 1.0;
    H_(1, 1) = 1.0;

    // Process noise (tune as needed)
    Q_ = MatrixXd::Zero(state_dim_, state_dim_);
    // modest model noise on velocity; tiny on position; yaw noise moderate
    Q_(0,0) = 1e-3;  Q_(1,1) = 1e-3;
    Q_(2,2) = 5e-2;  Q_(3,3) = 5e-2;
    Q_(4,4) = 1e-2;

    // Measurement noise (GPS position)
    R_ = MatrixXd::Zero(meas_dim_, meas_dim_);
    R_(0,0) = 3.0;   // ~sqrt(3 m^2) std → ≈1.7 m
    R_(1,1) = 3.0;

    // Initial state / covariance
    x_ = VectorXd::Zero(state_dim_);
    P_ = MatrixXd::Identity(state_dim_, state_dim_) * 10.0;
}

void EKF::init(const VectorXd& x0) {
    if (x0.size() != state_dim_) {
        throw std::runtime_error("EKF::init: wrong state size");
    }
    x_ = x0;
    P_.setIdentity();
    P_ *= 10.0;
}

void EKF::setDeltaT(double dt) {
    dt_ = dt;
    // Refresh F with new dt
    F_.setIdentity();
    F_(0, 2) = dt_;
    F_(1, 3) = dt_;
}

void EKF::predict(double ax_body, double yaw_rate) {
    // Unpack state
    double x = x_(0), y = x_(1), vx = x_(2), vy = x_(3), yaw = x_(4);
    // Integrate yaw
    double yaw_new = yaw + yaw_rate * dt_;
    while (yaw_new > M_PI) yaw_new -= 2.0 * M_PI;
    while (yaw_new < -M_PI) yaw_new += 2.0 * M_PI;
    // Body accel to world (flat assumption)
    double ax_w = ax_body * std::cos(yaw);
    double ay_w = ax_body * std::sin(yaw);
    // Integrate motion
    double vx_new = vx + ax_w * dt_;
    double vy_new = vy + ay_w * dt_;
    double x_new  = x + vx * dt_ + 0.5 * ax_w * dt_ * dt_;
    double y_new  = y + vy * dt_ + 0.5 * ay_w * dt_ * dt_;
    x_(0) = x_new; x_(1) = y_new; x_(2) = vx_new; x_(3) = vy_new; x_(4) = yaw_new;
    // Covariance propagate
    F_.setIdentity();
    F_(0, 2) = dt_;
    F_(1, 3) = dt_;
    P_ = F_ * P_ * F_.transpose() + Q_;
}

void EKF::update(const VectorXd& z) {
    if (z.size() != meas_dim_) {
        throw std::runtime_error("EKF::update: wrong measurement size");
    }
    // Innovation
    VectorXd y = z - H_ * x_;
    // Innovation covariance
    MatrixXd S = H_ * P_ * H_.transpose() + R_;
    // Kalman gain
    MatrixXd K = P_ * H_.transpose() * S.inverse();

    // Update
    x_ = x_ + K * y;
    MatrixXd I = MatrixXd::Identity(state_dim_, state_dim_);
    P_ = (I - K * H_) * P_;
}

VectorXd EKF::state() const {
    return x_;
}
