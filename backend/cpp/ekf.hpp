#ifndef EKF_HPP
#define EKF_HPP

#include <Eigen/Dense>

class EKF {
public:
    explicit EKF(double dt);

    void init(const Eigen::VectorXd& x0);

    // NEW: update Δt each step (used by predict())
    void setDeltaT(double dt);

    // Predict with IMU inputs: ax_body (m/s^2 forward), yaw_rate (rad/s)
    void predict(double ax_body, double yaw_rate);
    void update(const Eigen::VectorXd& z);
    Eigen::VectorXd state() const;

private:
    double dt_;
    int state_dim_;
    int meas_dim_;

    // State transition, measurement, covariances, etc.
    // Dynamic Jacobian (F) and static H for position measurement
    Eigen::MatrixXd F_;
    Eigen::MatrixXd H_;
    Eigen::MatrixXd Q_;
    Eigen::MatrixXd R_;
    Eigen::MatrixXd P_;
    Eigen::VectorXd x_;
};

#endif
