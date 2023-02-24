#include <functional>
#include <stdexcept>
#include <thread>

#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>
#include <geometry_msgs/msg/twist.hpp>

#include <stdlib.h>
#include <signal.h>
#include <stdio.h>
#ifdef _WIN32
# include <windows.h>
#else
# include <termios.h>
# include <unistd.h>
#endif

#include "turtle_bot_5/srv/save_path.hpp"
#include "turtle_bot_5/msg/float32_multi_array.hpp"

static constexpr char KEYCODE_RIGHT = 0x43;
static constexpr char KEYCODE_LEFT = 0x44;
static constexpr char KEYCODE_UP = 0x41;
static constexpr char KEYCODE_DOWN = 0x42;
static constexpr char KEYCODE_Q = 0x71;

bool running = true;

turtle_bot_5::msg::Float32MultiArray res;


class KeyboardReader final
{
public:
  KeyboardReader()
  {
#ifdef _WIN32
    hstdin_ = GetStdHandle(STD_INPUT_HANDLE);
    if (hstdin_ == INVALID_HANDLE_VALUE)
    {
      throw std::runtime_error("Failed to get stdin handle");
    }
    if (!GetConsoleMode(hstdin_, &old_mode_))
    {
      throw std::runtime_error("Failed to get old console mode");
    }
    DWORD new_mode = ENABLE_PROCESSED_INPUT;  // for Ctrl-C processing
    if (!SetConsoleMode(hstdin_, new_mode))
    {
      throw std::runtime_error("Failed to set new console mode");
    }
#else
    // get the console in raw mode
    if (tcgetattr(0, &cooked_) < 0)
    {
      throw std::runtime_error("Failed to get old console mode");
    }
    struct termios raw;
    memcpy(&raw, &cooked_, sizeof(struct termios));
    raw.c_lflag &=~ (ICANON | ECHO);
    // Setting a new line, then end of file
    raw.c_cc[VEOL] = 1;
    raw.c_cc[VEOF] = 2;
    raw.c_cc[VTIME] = 1;
    raw.c_cc[VMIN] = 0;
    if (tcsetattr(0, TCSANOW, &raw) < 0)
    {
      throw std::runtime_error("Failed to set new console mode");
    }
#endif
  }

  char readOne()
  {
    char c = 0;

#ifdef _WIN32
    INPUT_RECORD record;
    DWORD num_read;
    switch (WaitForSingleObject(hstdin_, 0.001))
    {
    case WAIT_OBJECT_0:
      if (!ReadConsoleInput(hstdin_, &record, 1, &num_read))
      {
        throw std::runtime_error("Read failed");
      }

      if (record.EventType != KEY_EVENT || !record.Event.KeyEvent.bKeyDown) {
        break;
      }

      if (record.Event.KeyEvent.wVirtualKeyCode == VK_LEFT)
      {
        c = KEYCODE_LEFT;
      }
      else if (record.Event.KeyEvent.wVirtualKeyCode == VK_UP)
      {
        c = KEYCODE_UP;
      }
      else if (record.Event.KeyEvent.wVirtualKeyCode == VK_RIGHT)
      {
        c = KEYCODE_RIGHT;
      }
      else if (record.Event.KeyEvent.wVirtualKeyCode == VK_DOWN)
      {
        c = KEYCODE_DOWN;
      }
      else if (record.Event.KeyEvent.wVirtualKeyCode == 0x51)
      {
        c = KEYCODE_Q;
      }
      break;

    case WAIT_TIMEOUT:
      break;
    }

#else
    int rc = read(0, &c, 1);
    if (rc < 0)
    {
      throw std::runtime_error("read failed");
    }
#endif

    return c;
  }

  ~KeyboardReader()
  {
#ifdef _WIN32
    SetConsoleMode(hstdin_, old_mode_);
#else
    tcsetattr(0, TCSANOW, &cooked_);
#endif
  }

private:
#ifdef _WIN32
  HANDLE hstdin_;
  DWORD old_mode_;
#else
  struct termios cooked_;
#endif
};

class TurtleBotTeleop final
{
public:
  TurtleBotTeleop(rclcpp::Node::SharedPtr nh)
  {
    rclcpp::Node::SharedPtr nh_ = nh;
    twist_pub_ = nh_->create_publisher<geometry_msgs::msg::Twist>("turtlebot_cmdVel", 1);
  }

  int keyLoop(float p_linear, float p_angular)
  {
    char c;

    puts("---------------------------");
    puts("\nReading from keyboard");
    puts("Use arrow keys to move the turtle.");
    puts("'Q' to quit.");

    while (running)
    {
      c = input_.readOne();

      double linear = 0.0;
      double angular = 0.0;

      switch(c)
      {
      case KEYCODE_LEFT:
        angular = p_angular;

        res.data.push_back(4);
        break;
      case KEYCODE_RIGHT:
        angular = -p_angular;

        res.data.push_back(3);
        break;
      case KEYCODE_UP:
        linear = p_linear;

        res.data.push_back(1);
        break;
      case KEYCODE_DOWN:
        linear = -p_linear;

        res.data.push_back(2);
        break;
      case KEYCODE_Q:
        running = false;
        break;
      default:
        break;
      }

      if (running && (linear != 0.0 || angular != 0.0))
      {
        geometry_msgs::msg::Twist twist;
        twist.angular.z = angular;
        twist.linear.x = linear;
        twist_pub_->publish(twist);

        twist.angular.z = 0;
        twist.linear.x = 0;
        twist_pub_->publish(twist);
      }
      else if(linear == 0.0 && angular == 0.0 && c==0 )
      {
        res.data.push_back(0);
      }
    }

    return 0;
  }

private:
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr twist_pub_;
  KeyboardReader input_;
};

#ifdef _WIN32
BOOL WINAPI quit(DWORD ctrl_type)
{
  (void)ctrl_type;
  running = false;
  return true;
}
#else
void quit(int sig)
{
  (void)sig;
  running = false;
}
#endif

void sendPath(const std::shared_ptr<turtle_bot_5::srv::SavePath::Request>,
          std::shared_ptr<turtle_bot_5::srv::SavePath::Response> response)
  {
    response-> path = res;
  }

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);

  std::shared_ptr<rclcpp::Node> node = rclcpp::Node::make_shared("turtle_bot_teleop");

  float linear;
  float angular;

  printf("Input the linear velocity: ");
  scanf("%f", &linear);
    
  printf("Input the angular velocity: ");
  scanf("%f", &angular);

  TurtleBotTeleop teleop_turtle(node);

  res.data.clear();
  res.data.push_back(linear);
  res.data.push_back(angular);

  teleop_turtle.keyLoop(linear, angular);

  rclcpp::Service<turtle_bot_5::srv::SavePath>::SharedPtr service =
    node->create_service<turtle_bot_5::srv::SavePath>("save_path", &sendPath);

  RCLCPP_INFO(rclcpp::get_logger("rclcpp"), "Finished");

  rclcpp::spin(node);
  rclcpp::shutdown();

}
