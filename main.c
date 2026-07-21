/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */
typedef struct {
    GPIO_TypeDef *port;
    uint16_t pul_pin;
    uint16_t dir_pin;
} Motor;
/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;
UART_HandleTypeDef huart2;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART2_UART_Init(void);
static void MX_USART1_UART_Init(void);
/* USER CODE BEGIN PFP */
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART2_UART_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */
  uint8_t rx;
  uint8_t s_rx;
  char buffer[20];
  char response[20];
  int idx = 0;

  float elevation = 90;
  float azimuth = 90;
  int delay = 10;

  float el_angle_per_step = 0.09;
  float az_angle_per_step = 0.135;


  Motor motor_az = {
		  .port = GPIOB,
		  .pul_pin = GPIO_PIN_6,
		  .dir_pin = GPIO_PIN_5,
  };

  Motor motor_el = {
		  .port = GPIOA,
		  .pul_pin = GPIO_PIN_4,
		  .dir_pin = GPIO_PIN_7,
  };
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */

  while (1)
  {
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
	  if (HAL_UART_Receive(&huart1, &rx, 1, 100) != HAL_OK)
	          continue;

	      if (rx == '\r')
	          continue;

	      if (rx != '\n')
	      {
	          if (idx < (int)(sizeof(buffer) - 1))
	          {
	              buffer[idx++] = rx;
	          }
	          else
	          {
	              idx = 0;
	              HAL_UART_Transmit(&huart1, (uint8_t *)"ERR:overflow\r\n", 14, 100);
	          }
	          continue;
	      }

	      buffer[idx] = '\0';
//	      HAL_UART_Transmit(&huart1, (uint8_t *)"XXX: ", 4, 100);
//	      HAL_UART_Transmit(&huart1, (uint8_t *)buffer, idx, 100);
//	      HAL_UART_Transmit(&huart1, (uint8_t *)"\r\n", 2, 100);


	      if (buffer[0] == 'R'){
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)"R\r\n", 3, 100);
	    	  snprintf(response, sizeof(response), "A%.3f\r\n", azimuth);
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
	    	  snprintf(response, sizeof(response), "E%.3f\r\n", elevation);
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
	    	  snprintf(response, sizeof(response), "T%d\r\n", delay);
			  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)"D\r\n", 3, 100);
	    	  idx = 0;
	    	  continue;
	      }

	      if (buffer[0] == 'T'){
	    	  delay = atoi(&buffer[1]);
	     	  snprintf(response, sizeof(response), "T%d\r\n", delay);
			  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
	    	  idx = 0;
	    	  continue;
	      }

	      if (buffer[0] == 'O'){
	    	  elevation = 90;
	    	  azimuth = 90;
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)"O\r\n", 3, 100);
			  idx = 0;
			  continue;
		  }

	      if (idx < 4)
	      {
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)"ERR:short buf=", 14, 100);
	    	  HAL_UART_Transmit(&huart1, (uint8_t *)buffer, idx, 100);
	          HAL_UART_Transmit(&huart1, (uint8_t *)"\r\n", 2, 100);
	          idx = 0;
	          continue;
	      }
	      /*
	       Assuming the command comes in the form: "+1000-1000" Where (+, -) represents the
	       direction, and the associated value represents the steps It can also be assumed
	       that the order will be azimuth first, then elevation. Lastly, the maximum number
	       of steps would be what it takes to go 360 degrees; it should not be possible to
	       receive a single command that exceeds this due to practical constraints. Based on
	       my current setup, 4000 steps is equivalent to 360 degrees for both azimuth and
	       elevation This is why we set the steps buffer to 5, since the maximum value
	       is "4000\0" including the null terminator
	      */

	      char direction_az = buffer[0];
	      char direction_el = buffer[5];

	      char steps_az_arr[5];
	      char steps_el_arr[5];

	      steps_az_arr[0] = buffer[1];
	      steps_az_arr[1] = buffer[2];
	      steps_az_arr[2] = buffer[3];
	      steps_az_arr[3] = buffer[4];
	      steps_az_arr[4] = '\0';

	      steps_el_arr[0] = buffer[6];
	      steps_el_arr[1] = buffer[7];
	      steps_el_arr[2] = buffer[8];
	      steps_el_arr[3] = buffer[9];
	      steps_el_arr[4] = '\0';

	      int steps_az = atoi(steps_az_arr);
	      int steps_el = atoi(steps_el_arr);

	      int stopped   = 0;

		  if (direction_az == '+')
		  {
			  if (steps_az > 0)
			  {
				  HAL_GPIO_WritePin(motor_az.port, motor_az.dir_pin, GPIO_PIN_SET);

				  for (int i = 0; i < steps_az && !stopped; i++)
				  {
					  if (HAL_UART_Receive(&huart1, &s_rx, 1, 10) == HAL_OK)
					  {
						  if (s_rx == 'S')
						  {
							  HAL_UART_Transmit(&huart1, (uint8_t *)"S\r\n", 3, 100);
							  stopped = 1;
							  break;
						  }
					  }
					  HAL_GPIO_WritePin(motor_az.port, motor_az.pul_pin, GPIO_PIN_SET);
					  HAL_Delay(delay);
					  HAL_GPIO_WritePin(motor_az.port, motor_az.pul_pin, GPIO_PIN_RESET);
					  HAL_Delay(delay);

					  azimuth += az_angle_per_step;
					  if (azimuth >= 360.0){
						  azimuth -= 360;
					  }
					  snprintf(response, sizeof(response), "A%.3f\r\n", azimuth);
					  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
				  }
			  }
		  }
		  else if (direction_az == '-')
		  {
			  if (steps_az > 0)
			  {
			  HAL_GPIO_WritePin(motor_az.port, motor_az.dir_pin, GPIO_PIN_RESET);
				  for (int i = 0; i < steps_az && !stopped; i++)
				  {
					  if (HAL_UART_Receive(&huart1, &s_rx, 1, 10) == HAL_OK)
					  {
						  if (s_rx == 'S')
						  {
							  HAL_UART_Transmit(&huart1, (uint8_t *)"S\r\n", 3, 100);
							  stopped = 1;
							  break;
						  }
					  }
					  HAL_GPIO_WritePin(motor_az.port, motor_az.pul_pin, GPIO_PIN_SET);
					  HAL_Delay(delay);
					  HAL_GPIO_WritePin(motor_az.port, motor_az.pul_pin, GPIO_PIN_RESET);
					  HAL_Delay(delay);

					  azimuth -= az_angle_per_step;
					  if (azimuth < 0.0){
						  azimuth += 360;
					  }
					  snprintf(response, sizeof(response), "A%.3f\r\n", azimuth);
					  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
				  }

			  }
		  }
		  else
		  {
			  HAL_UART_Transmit(&huart1, (uint8_t *)"ERR:dir\r\n", 9, 100);
			  idx = 0;
			  continue;
		  }

		  if (direction_el == '+')
		  {
			  if (steps_el > 0){
			  HAL_GPIO_WritePin(motor_el.port, motor_el.dir_pin, GPIO_PIN_RESET);
				  for (int i = 0; i < steps_el && !stopped; i++)
				  {
					  if (HAL_UART_Receive(&huart1, &s_rx, 1, 10) == HAL_OK)
					  {
						  if (s_rx == 'S')
						  {
							  HAL_UART_Transmit(&huart1, (uint8_t *)"S\r\n", 3, 100);
							  stopped = 1;
							  break;
						  }
					  }
					  HAL_GPIO_WritePin(motor_el.port, motor_el.pul_pin, GPIO_PIN_SET);
					  HAL_Delay(delay);
					  HAL_GPIO_WritePin(motor_el.port, motor_el.pul_pin, GPIO_PIN_RESET);
					  HAL_Delay(delay);

					  elevation += el_angle_per_step;
					  snprintf(response, sizeof(response), "E%.3f\r\n", elevation);
					  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
				  }

			  }
		  }
		  else if (direction_el == '-')
		  {
			  if (steps_el > 0){
			  HAL_GPIO_WritePin(motor_el.port, motor_el.dir_pin, GPIO_PIN_SET);
				  for (int i = 0; i < steps_el && !stopped; i++)
				  {
					  if (HAL_UART_Receive(&huart1, &s_rx, 1, 10) == HAL_OK)
					  {
						  if (s_rx == 'S')
						  {
							  HAL_UART_Transmit(&huart1, (uint8_t *)"S\r\n", 3, 100);
							  stopped = 1;
							  break;
						  }
					  }
					  HAL_GPIO_WritePin(motor_el.port, motor_el.pul_pin, GPIO_PIN_SET);
					  HAL_Delay(delay);
					  HAL_GPIO_WritePin(motor_el.port, motor_el.pul_pin, GPIO_PIN_RESET);
					  HAL_Delay(delay);

					  elevation -= el_angle_per_step;
					  snprintf(response, sizeof(response), "E%.3f\r\n", elevation);
					  HAL_UART_Transmit(&huart1, (uint8_t *)response, strlen(response), 100);
				  }

			  }
		  }
		  else
		  {
			  HAL_UART_Transmit(&huart1, (uint8_t *)"ERR:dir\r\n", 9, 100);
			  idx = 0;
			  continue;
		  }

	  if (!stopped)
		  HAL_UART_Transmit(&huart1, (uint8_t *)"D\r\n", 3, 100);

	  idx = 0;
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure LSE Drive Capability
  */
  HAL_PWR_EnableBkUpAccess();
  __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_LOW);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE|RCC_OSCILLATORTYPE_MSI;
  RCC_OscInitStruct.LSEState = RCC_LSE_ON;
  RCC_OscInitStruct.MSIState = RCC_MSI_ON;
  RCC_OscInitStruct.MSICalibrationValue = 0;
  RCC_OscInitStruct.MSIClockRange = RCC_MSIRANGE_6;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_MSI;
  RCC_OscInitStruct.PLL.PLLM = 1;
  RCC_OscInitStruct.PLL.PLLN = 16;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
  RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Enable MSI Auto calibration
  */
  HAL_RCCEx_EnableMSIPLLMode();
}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief USART2 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART2_UART_Init(void)
{

  /* USER CODE BEGIN USART2_Init 0 */

  /* USER CODE END USART2_Init 0 */

  /* USER CODE BEGIN USART2_Init 1 */

  /* USER CODE END USART2_Init 1 */
  huart2.Instance = USART2;
  huart2.Init.BaudRate = 115200;
  huart2.Init.WordLength = UART_WORDLENGTH_8B;
  huart2.Init.StopBits = UART_STOPBITS_1;
  huart2.Init.Parity = UART_PARITY_NONE;
  huart2.Init.Mode = UART_MODE_TX_RX;
  huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart2.Init.OverSampling = UART_OVERSAMPLING_16;
  huart2.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart2.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart2) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART2_Init 2 */

  /* USER CODE END USART2_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4|GPIO_PIN_7, GPIO_PIN_RESET);

  /*Configure GPIO pin Output Level */
  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_5|GPIO_PIN_6, GPIO_PIN_RESET);

  /*Configure GPIO pins : PA4 PA7 */
  GPIO_InitStruct.Pin = GPIO_PIN_4|GPIO_PIN_7;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

  /*Configure GPIO pins : PB5 PB6 */
  GPIO_InitStruct.Pin = GPIO_PIN_5|GPIO_PIN_6;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

  /* USER CODE BEGIN MX_GPIO_Init_2 */

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  Period elapsed callback in non blocking mode
  * @note   This function is called  when TIM1 interrupt took place, inside
  * HAL_TIM_IRQHandler(). It makes a direct call to HAL_IncTick() to increment
  * a global variable "uwTick" used as application time base.
  * @param  htim : TIM handle
  * @retval None
  */
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
  /* USER CODE BEGIN Callback 0 */

  /* USER CODE END Callback 0 */
  if (htim->Instance == TIM1)
  {
    HAL_IncTick();
  }
  /* USER CODE BEGIN Callback 1 */

  /* USER CODE END Callback 1 */
}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
